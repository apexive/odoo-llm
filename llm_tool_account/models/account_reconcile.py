"""Reconciliation tools: find unreconciled items, reconcile, suggest matches"""

import logging
from collections import defaultdict
from typing import Optional

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.llm_tool.decorators import llm_tool

_logger = logging.getLogger(__name__)


class AccountReconcile(models.Model):
    _name = "account.tool.reconcile"
    _inherit = "account.tool.mixin"
    _description = "LLM tools for reconciliation"

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def account_get_unreconciled(
        self,
        type: str = "all",
        partner: Optional[str] = None,
        journal: Optional[str] = None,
        limit: int = 100,
    ) -> dict:
        """List unreconciled journal items

        Returns journal items that have not been fully reconciled, filtered
        by type. Useful for identifying items that need attention.

        Args:
            type: Filter type - "bank" (bank journal items),
                  "invoices" (receivable from customer invoices),
                  "bills" (payable from vendor bills),
                  "payments" (payment journal items),
                  "all" (all reconcilable, default)
            partner: Filter by partner name (optional)
            journal: Filter by journal code or name (optional)
            limit: Maximum results (default: 100)

        Returns:
            Dictionary with unreconciled items grouped by type
        """
        MoveLine = self.env["account.move.line"]

        domain = [
            ("reconciled", "=", False),
            ("parent_state", "=", "posted"),
            ("account_id.reconcile", "=", True),
        ]

        type_lower = type.lower()
        if type_lower == "bank":
            bank_journals = self.env["account.journal"].search(
                [("type", "in", ("bank", "cash"))]
            )
            domain.append(("journal_id", "in", bank_journals.ids))
        elif type_lower == "invoices":
            domain.extend(
                [
                    ("account_id.account_type", "=", "asset_receivable"),
                    ("move_id.move_type", "in", ("out_invoice", "out_refund")),
                ]
            )
        elif type_lower == "bills":
            domain.extend(
                [
                    ("account_id.account_type", "=", "liability_payable"),
                    ("move_id.move_type", "in", ("in_invoice", "in_refund")),
                ]
            )
        elif type_lower == "payments":
            domain.append(("move_id.move_type", "=", "entry"))
            domain.append(
                (
                    "account_id.account_type",
                    "in",
                    ("asset_receivable", "liability_payable"),
                )
            )
        elif type_lower != "all":
            raise UserError(
                _("Invalid type '%s'. Use: bank, invoices, bills, " "payments, or all")
                % type
            )

        if partner:
            domain.append(("partner_id", "=", self._resolve_partner(partner).id))
        if journal:
            domain.append(("journal_id", "=", self._resolve_journal(journal).id))

        lines = MoveLine.search(domain, limit=limit, order="date desc, id desc")

        items = []
        for line in lines:
            items.append(
                {
                    "id": line.id,
                    "date": str(line.date),
                    "move_name": line.move_name,
                    "account_code": line.account_id.code,
                    "partner_name": line.partner_id.name or "",
                    "label": line.name or "",
                    "debit": line.debit,
                    "credit": line.credit,
                    "amount_residual": line.amount_residual,
                    "date_maturity": str(line.date_maturity)
                    if line.date_maturity
                    else "",
                }
            )

        return {
            "type_filter": type,
            "items": items,
            "count": len(items),
        }

    @llm_tool(destructive_hint=True)
    def account_reconcile(
        self,
        line_ids: list,
        write_off_account: Optional[str] = None,
        write_off_label: Optional[str] = None,
        allow_partial: bool = False,
    ) -> dict:
        """Reconcile journal items

        Matches debit and credit journal items together. The items must
        be on reconcilable accounts and belong to the same account.

        If the amounts don't balance exactly, you can either allow partial
        reconciliation or specify a write-off account for the difference.

        Args:
            line_ids: List of journal item IDs to reconcile together
            write_off_account: Account code for write-off difference (optional)
            write_off_label: Label for write-off line (optional)
            allow_partial: Allow partial reconciliation if amounts don't
                           match (default: False)

        Returns:
            Dictionary with reconciliation result
        """
        MoveLine = self.env["account.move.line"]

        if len(line_ids) < 2:
            raise UserError(
                _("At least 2 journal items are required for reconciliation")
            )

        lines = MoveLine.browse(line_ids)
        if not lines.exists() or len(lines) != len(line_ids):
            raise UserError(_("Some journal item IDs were not found"))

        # Validate all lines are on reconcilable accounts
        non_reconcilable = lines.filtered(lambda line: not line.account_id.reconcile)
        if non_reconcilable:
            raise UserError(
                _("Lines on non-reconcilable accounts: %s")
                % ", ".join(non_reconcilable.mapped("account_id.code"))
            )

        # Check all on same account
        account_ids = lines.mapped("account_id").ids
        if len(account_ids) > 1:
            raise UserError(
                _(
                    "All lines must be on the same account for reconciliation. "
                    "Found accounts: %s"
                )
                % ", ".join(lines.mapped("account_id.code"))
            )

        # Check balance
        total_residual = sum(lines.mapped("amount_residual"))

        if abs(total_residual) > 0.01 and not write_off_account and not allow_partial:
            raise UserError(
                _(
                    "Lines don't balance (residual: %.2f). Provide "
                    "write_off_account or set allow_partial=True"
                )
                % total_residual
            )

        if write_off_account and abs(total_residual) > 0.01:
            wo_account = self._resolve_accounts(write_off_account)
            if len(wo_account) != 1:
                raise UserError(
                    _("Write-off account '%s' must match exactly one account")
                    % write_off_account
                )

            # Create write-off and reconcile
            lines.reconcile(
                write_off_vals={
                    "account_id": wo_account.id,
                    "name": write_off_label or _("Write-Off"),
                }
            )
        else:
            lines.reconcile()

        return {
            "reconciled_lines": len(lines),
            "line_ids": line_ids,
            "full_reconcile": lines[0].full_reconcile_id.name
            if lines[0].full_reconcile_id
            else None,
            "partial": allow_partial and abs(total_residual) > 0.01,
            "message": "Reconciliation completed successfully",
        }

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def account_suggest_matches(
        self,
        account: str,
        partner: Optional[str] = None,
        limit: int = 20,
    ) -> dict:
        """Suggest matching journal items for reconciliation

        Finds groups of unreconciled items that could be reconciled together
        based on matching amounts, partners, and references.

        Args:
            account: Account code to search for matches
            partner: Filter by partner name (optional)
            limit: Maximum suggestions (default: 20)

        Returns:
            Dictionary with suggested reconciliation groups
        """
        MoveLine = self.env["account.move.line"]

        accounts = self._resolve_accounts(account)
        if len(accounts) != 1:
            raise UserError(_("Account '%s' must match exactly one account") % account)

        domain = [
            ("account_id", "=", accounts.id),
            ("reconciled", "=", False),
            ("parent_state", "=", "posted"),
        ]

        if partner:
            domain.append(("partner_id", "=", self._resolve_partner(partner).id))

        lines = MoveLine.search(domain, order="date, id")

        # Group by partner for matching
        by_partner = defaultdict(lambda: {"debits": [], "credits": []})
        for line in lines:
            key = line.partner_id.id or 0
            entry = {
                "id": line.id,
                "date": str(line.date),
                "move_name": line.move_name,
                "label": line.name or "",
                "ref": line.ref or "",
                "amount_residual": line.amount_residual,
            }
            if line.amount_residual > 0:
                by_partner[key]["debits"].append(entry)
            elif line.amount_residual < 0:
                by_partner[key]["credits"].append(entry)

        suggestions = []
        for partner_id, items in by_partner.items():
            debits = items["debits"]
            credits = items["credits"]

            partner_name = ""
            if partner_id:
                partner_rec = self.env["res.partner"].browse(partner_id)
                partner_name = partner_rec.name

            # Find exact amount matches
            for d in debits:
                for c in credits:
                    if abs(d["amount_residual"] + c["amount_residual"]) < 0.01:
                        suggestions.append(
                            {
                                "partner": partner_name,
                                "match_type": "exact_amount",
                                "line_ids": [d["id"], c["id"]],
                                "debit_line": d,
                                "credit_line": c,
                                "difference": 0.0,
                            }
                        )

            if len(suggestions) >= limit:
                break

        return {
            "account_code": accounts.code,
            "account_name": accounts.name,
            "suggestions": suggestions[:limit],
            "count": len(suggestions[:limit]),
            "total_unreconciled_debits": sum(
                entry["amount_residual"]
                for items in by_partner.values()
                for entry in items["debits"]
            ),
            "total_unreconciled_credits": sum(
                entry["amount_residual"]
                for items in by_partner.values()
                for entry in items["credits"]
            ),
        }
