"""Data entry tools: create, post, unpost, and reverse journal entries"""

import logging
from typing import Optional

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.llm_tool.decorators import llm_tool

_logger = logging.getLogger(__name__)

MOVE_TYPE_MAP = {
    "invoice": "out_invoice",
    "bill": "in_invoice",
    "credit_note": "out_refund",
    "refund": "in_refund",
    "entry": "entry",
}


class AccountMoveEntry(models.Model):
    _name = "account.tool.entry"
    _inherit = "account.tool.mixin"
    _description = "LLM tools for journal entry data entry"

    @llm_tool(destructive_hint=True)
    def account_create_move(
        self,
        move_type: str,
        lines: list,
        partner: Optional[str] = None,
        date: Optional[str] = None,
        journal: Optional[str] = None,
        ref: Optional[str] = None,
        payment_terms: Optional[str] = None,
    ) -> dict:
        """Create a journal entry, invoice, or bill

        Creates a draft accounting document. Use move_type to specify the kind:
        - "invoice": Customer invoice (out_invoice)
        - "bill": Vendor bill (in_invoice)
        - "credit_note": Customer credit note (out_refund)
        - "refund": Vendor refund (in_refund)
        - "entry": Manual journal entry

        For invoices/bills, each line should have: account, description,
        quantity, price, and optionally tax.
        For journal entries, each line should have: account, description,
        debit, and credit.

        Args:
            move_type: Type of move ("invoice", "bill", "credit_note",
                       "refund", or "entry")
            lines: List of line dicts. For invoices/bills:
                   {"account": "400000", "description": "Service",
                    "quantity": 1, "price": 100.0, "tax": "VAT 21%"}
                   For entries:
                   {"account": "400000", "description": "Debit line",
                    "debit": 100.0, "credit": 0.0}
            partner: Partner name, ref, or VAT (required for invoices/bills)
            date: Accounting date in YYYY-MM-DD format (defaults to today)
            journal: Journal name, code, or type (auto-detected if not given)
            ref: Reference / description for the move
            payment_terms: Payment terms name (for invoices/bills only)

        Returns:
            Dictionary with created move details
        """
        if move_type not in MOVE_TYPE_MAP:
            raise UserError(
                _("Invalid move_type '%s'. Use: %s")
                % (move_type, ", ".join(MOVE_TYPE_MAP.keys()))
            )

        odoo_type = MOVE_TYPE_MAP[move_type]
        is_invoice = odoo_type != "entry"

        move_vals = {"move_type": odoo_type}

        if partner:
            move_vals["partner_id"] = self._resolve_partner(partner).id
        elif is_invoice:
            raise UserError(_("Partner is required for invoices and bills"))

        if date:
            move_vals["date"] = date
            if is_invoice:
                move_vals["invoice_date"] = date

        if journal:
            move_vals["journal_id"] = self._resolve_journal(journal).id

        if ref:
            move_vals["ref"] = ref

        if payment_terms and is_invoice:
            pt = self.env["account.payment.term"].search(
                [("name", "ilike", payment_terms)], limit=1
            )
            if not pt:
                raise UserError(_("Payment terms '%s' not found") % payment_terms)
            move_vals["invoice_payment_term_id"] = pt.id

        # Build line commands
        line_commands = []
        for idx, line_data in enumerate(lines):
            if not line_data.get("account"):
                raise UserError(_("Line %d: 'account' is required") % (idx + 1))

            account = self._resolve_accounts(line_data["account"])
            if len(account) > 1:
                raise UserError(
                    _("Line %d: account '%s' matches multiple accounts: %s")
                    % (
                        idx + 1,
                        line_data["account"],
                        ", ".join(account.mapped("code")),
                    )
                )

            line_vals = {
                "account_id": account.id,
                "name": line_data.get("description", "/"),
            }

            if is_invoice:
                line_vals["quantity"] = line_data.get("quantity", 1)
                line_vals["price_unit"] = line_data.get("price", 0.0)
                if line_data.get("tax"):
                    tax = self._resolve_tax(line_data["tax"])
                    line_vals["tax_ids"] = [(6, 0, [tax.id])]
            else:
                line_vals["debit"] = line_data.get("debit", 0.0)
                line_vals["credit"] = line_data.get("credit", 0.0)

            line_commands.append((0, 0, line_vals))

        move_vals["line_ids"] = line_commands

        move = self.env["account.move"].create(move_vals)

        return {
            "id": move.id,
            "name": move.name,
            "move_type": move_type,
            "state": move.state,
            "partner": move.partner_id.name or "",
            "date": str(move.date),
            "amount_total": move.amount_total,
            "line_count": len(move.line_ids),
            "message": f"Move '{move.name}' created as draft",
        }

    @llm_tool(destructive_hint=True)
    def account_post_moves(
        self,
        references: Optional[list] = None,
        partner: Optional[str] = None,
        move_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> dict:
        """Post (validate) draft journal entries

        Posts one or more draft journal entries, making them official.
        Provide either specific references or filters to select moves.

        Args:
            references: List of move names to post (e.g. ["INV/2025/0001"])
            partner: Filter by partner name (used with other filters)
            move_type: Filter by type ("invoice", "bill", "entry", etc.)
            date_from: Filter moves from this date (YYYY-MM-DD)
            date_to: Filter moves up to this date (YYYY-MM-DD)

        Returns:
            Dictionary with posting results
        """
        moves = self._find_moves_to_act(
            references=references,
            partner=partner,
            move_type=move_type,
            date_from=date_from,
            date_to=date_to,
            required_state="draft",
        )

        if not moves:
            raise UserError(_("No draft moves found matching the criteria"))

        moves.action_post()

        return {
            "posted_count": len(moves),
            "posted_moves": [{"name": m.name, "state": m.state} for m in moves],
            "message": f"{len(moves)} move(s) posted successfully",
        }

    @llm_tool(destructive_hint=True)
    def account_unpost_moves(
        self,
        references: list,
    ) -> dict:
        """Reset posted journal entries back to draft

        Unposting removes reconciliation on the move's lines and sets
        the move back to draft state. Respects lock dates.

        Args:
            references: List of move names to unpost (e.g. ["INV/2025/0001"])

        Returns:
            Dictionary with unposting results
        """
        moves = self.env["account.move"]
        for ref in references:
            moves |= self._resolve_move(ref)

        posted = moves.filtered(lambda m: m.state == "posted")
        if not posted:
            raise UserError(_("No posted moves found among the provided references"))

        posted.button_draft()

        return {
            "unposted_count": len(posted),
            "unposted_moves": [{"name": m.name, "state": m.state} for m in posted],
            "message": f"{len(posted)} move(s) reset to draft",
        }

    @llm_tool(destructive_hint=True)
    def account_reverse_move(
        self,
        reference: str,
        date: Optional[str] = None,
        journal: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> dict:
        """Reverse (cancel) a posted journal entry

        Creates a reversal entry that offsets the original. The original
        stays posted; a new offsetting entry is created and posted.

        Args:
            reference: Move name to reverse (e.g. "INV/2025/0001")
            date: Reversal date in YYYY-MM-DD format (defaults to today)
            journal: Journal for reversal (defaults to same journal)
            reason: Reason for reversal (stored as ref on reversal)

        Returns:
            Dictionary with reversal details
        """
        move = self._resolve_move(reference)
        if move.state != "posted":
            raise UserError(
                _("Move '%s' must be posted to reverse (current state: %s)")
                % (reference, move.state)
            )

        default_values = {}
        if date:
            default_values["date"] = date
        if journal:
            default_values["journal_id"] = self._resolve_journal(journal).id
        if reason:
            default_values["ref"] = _("Reversal of %s: %s") % (
                move.name,
                reason,
            )

        reversed_moves = move._reverse_moves(
            default_values_list=[default_values] if default_values else None,
            cancel=False,
        )
        reversed_moves.action_post()

        return {
            "original_move": move.name,
            "reversal_move": reversed_moves[0].name if reversed_moves else "",
            "reversal_date": str(reversed_moves[0].date) if reversed_moves else "",
            "state": reversed_moves[0].state if reversed_moves else "",
            "message": f"Move '{move.name}' reversed as '{reversed_moves[0].name}'",
        }

    def _find_moves_to_act(
        self,
        references=None,
        partner=None,
        move_type=None,
        date_from=None,
        date_to=None,
        required_state=None,
    ):
        """Find moves by references or filters."""
        Move = self.env["account.move"]

        if references:
            moves = Move
            for ref in references:
                moves |= self._resolve_move(ref)
            if required_state:
                moves = moves.filtered(lambda m: m.state == required_state)
            return moves

        domain = []
        if required_state:
            domain.append(("state", "=", required_state))
        if partner:
            domain.append(("partner_id", "=", self._resolve_partner(partner).id))
        if move_type:
            odoo_type = MOVE_TYPE_MAP.get(move_type, move_type)
            domain.append(("move_type", "=", odoo_type))
        if date_from:
            domain.append(("date", ">=", date_from))
        if date_to:
            domain.append(("date", "<=", date_to))

        return Move.search(domain)
