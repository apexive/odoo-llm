"""Ledger tools: journal items with running balances"""

import logging
from typing import Optional

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.llm_tool.decorators import llm_tool

_logger = logging.getLogger(__name__)


class AccountLedger(models.Model):
    _name = "account.tool.ledger"
    _inherit = "account.tool.mixin"
    _description = "LLM tools for general ledger"

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def account_get_ledger(
        self,
        accounts: str,
        date_from: str,
        date_to: str,
        partner: Optional[str] = None,
        journal: Optional[str] = None,
        reconciled: Optional[bool] = None,
        target_move: str = "posted",
        limit: int = 200,
        offset: int = 0,
    ) -> dict:
        """Get general ledger (journal items) with running balance

        Returns individual journal items for the specified accounts, including
        an initial balance row and running balance on each line. Useful for
        reviewing account activity in detail.

        Args:
            accounts: Account code, pattern (e.g. "111101"), or type
                      shortcut ("bank", "receivable", etc.)
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            partner: Filter by partner name (optional)
            journal: Filter by journal code or name (optional)
            reconciled: Filter by reconciliation status (optional)
            target_move: "posted" (default) or "all" entries
            limit: Maximum items to return (default: 200)
            offset: Skip first N items for pagination (default: 0)

        Returns:
            Dictionary with initial balance and journal items
        """
        resolved_accounts = self._resolve_accounts(accounts)
        if not resolved_accounts:
            raise UserError(_("No accounts found for '%s'") % accounts)

        account_ids = resolved_accounts.ids

        # Build extra domain
        extra_domain = []
        if partner:
            extra_domain.append(("partner_id", "=", self._resolve_partner(partner).id))
        if journal:
            extra_domain.append(("journal_id", "=", self._resolve_journal(journal).id))
        if reconciled is not None:
            extra_domain.append(("reconciled", "=", reconciled))

        # Compute initial balance
        initial_balance = self._compute_ledger_initial_balance(
            account_ids, date_from, target_move, extra_domain
        )

        # Fetch period lines
        domain = [
            ("account_id", "in", account_ids),
            ("date", ">=", date_from),
            ("date", "<=", date_to),
        ] + extra_domain

        if target_move == "posted":
            domain.append(("parent_state", "=", "posted"))
        else:
            domain.append(("parent_state", "!=", "cancel"))

        total_count = self.env["account.move.line"].search_count(domain)

        lines = self.env["account.move.line"].search(
            domain,
            limit=limit,
            offset=offset,
            order="date, move_name, id",
        )

        # Build result with running balance
        running = initial_balance
        items = []
        for line in lines:
            running += line.balance
            items.append(
                {
                    "id": line.id,
                    "date": str(line.date),
                    "move_name": line.move_name,
                    "journal_code": line.journal_id.code,
                    "account_code": line.account_id.code,
                    "partner_name": line.partner_id.name or "",
                    "label": line.name or "",
                    "ref": line.ref or "",
                    "debit": line.debit,
                    "credit": line.credit,
                    "balance": running,
                    "reconciled": line.reconciled,
                    "matching_number": line.matching_number or "",
                }
            )

        return {
            "accounts": [{"code": a.code, "name": a.name} for a in resolved_accounts],
            "date_from": date_from,
            "date_to": date_to,
            "initial_balance": initial_balance,
            "items": items,
            "item_count": len(items),
            "total_count": total_count,
            "has_more": (offset + limit) < total_count,
        }

    def _compute_ledger_initial_balance(
        self, account_ids, date_from, target_move, extra_domain
    ):
        """Compute initial balance for ledger, respecting BS/P&L logic."""
        MoveLine = self.env["account.move.line"]
        accounts = self.env["account.account"].browse(account_ids)

        total_initial = 0.0

        bs_ids = [a.id for a in accounts if self._is_bs_account(a)]
        pl_ids = [a.id for a in accounts if not self._is_bs_account(a)]

        # BS: all time < date_from
        if bs_ids:
            domain = [
                ("account_id", "in", bs_ids),
                ("date", "<", date_from),
            ] + extra_domain
            if target_move == "posted":
                domain.append(("parent_state", "=", "posted"))

            groups = MoveLine._read_group(
                domain=domain,
                groupby=[],
                aggregates=["balance:sum"],
            )
            if groups:
                total_initial += groups[0][0] or 0.0

        # P&L: FY start to date_from
        if pl_ids:
            fy_start = self._get_fy_start_date(date_from)
            domain = [
                ("account_id", "in", pl_ids),
                ("date", ">=", str(fy_start)),
                ("date", "<", date_from),
            ] + extra_domain
            if target_move == "posted":
                domain.append(("parent_state", "=", "posted"))

            groups = MoveLine._read_group(
                domain=domain,
                groupby=[],
                aggregates=["balance:sum"],
            )
            if groups:
                total_initial += groups[0][0] or 0.0

        return total_initial
