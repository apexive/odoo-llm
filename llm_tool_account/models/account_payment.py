"""Payment tools: register payments against invoices and bills"""

import logging
from typing import Optional

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.llm_tool.decorators import llm_tool

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _name = "account.tool.payment"
    _inherit = "account.tool.mixin"
    _description = "LLM tools for payment registration"

    @llm_tool(destructive_hint=True)
    def account_register_payment(
        self,
        move_references: Optional[list] = None,
        partner: Optional[str] = None,
        amount: Optional[float] = None,
        date: Optional[str] = None,
        journal: Optional[str] = None,
        memo: Optional[str] = None,
        group_payment: bool = True,
    ) -> dict:
        """Register a payment for invoices or bills

        Creates and posts a payment. Either provide move_references to pay
        specific invoices/bills, or provide partner + amount for an
        unmatched payment.

        When paying multiple invoices for the same partner, they are grouped
        into a single payment by default.

        Args:
            move_references: List of invoice/bill names to pay
                             (e.g. ["INV/2025/0001", "INV/2025/0002"])
            partner: Partner name (used with amount for unmatched payments)
            amount: Payment amount (required if no move_references)
            date: Payment date in YYYY-MM-DD format (defaults to today)
            journal: Payment journal name or code (e.g. "Bank", "BNK1")
            memo: Payment memo / communication
            group_payment: Group multiple invoices into one payment
                           (default: True)

        Returns:
            Dictionary with payment details
        """
        Move = self.env["account.move"]

        if move_references:
            moves = Move
            for ref in move_references:
                moves |= self._resolve_move(ref)

            # Validate moves are payable
            payable = moves.filtered(
                lambda m: m.state == "posted"
                and m.payment_state in ("not_paid", "partial")
                and m.move_type
                in ("out_invoice", "in_invoice", "out_refund", "in_refund")
            )
            if not payable:
                raise UserError(
                    _(
                        "No payable posted invoices/bills found among "
                        "the provided references"
                    )
                )

            # Use payment register wizard
            ctx = {
                "active_model": "account.move",
                "active_ids": payable.ids,
            }
            wizard_vals = {"group_payment": group_payment}

            if date:
                wizard_vals["payment_date"] = date
            if journal:
                wizard_vals["journal_id"] = self._resolve_journal(journal).id
            if memo:
                wizard_vals["communication"] = memo

            wizard = (
                self.env["account.payment.register"]
                .with_context(**ctx)
                .create(wizard_vals)
            )
            action = wizard.action_create_payments()

        elif partner and amount:
            # Direct payment without invoice matching
            partner_rec = self._resolve_partner(partner)

            payment_vals = {
                "partner_id": partner_rec.id,
                "amount": abs(amount),
                "payment_type": "inbound" if amount > 0 else "outbound",
                "partner_type": "customer" if amount > 0 else "supplier",
            }

            if date:
                payment_vals["date"] = date
            if journal:
                payment_vals["journal_id"] = self._resolve_journal(journal).id
            if memo:
                payment_vals["ref"] = memo

            payment = self.env["account.payment"].create(payment_vals)
            payment.action_post()

            return {
                "payment_id": payment.id,
                "name": payment.name,
                "amount": payment.amount,
                "date": str(payment.date),
                "partner": payment.partner_id.name,
                "journal": payment.journal_id.name,
                "state": payment.state,
                "message": f"Payment '{payment.name}' created and posted",
            }

        else:
            raise UserError(
                _(
                    "Provide either move_references to pay invoices, "
                    "or partner + amount for a direct payment"
                )
            )

        # Extract payment info from wizard action result
        if isinstance(action, dict) and action.get("res_id"):
            payment = self.env["account.payment"].browse(action["res_id"])
            return {
                "payment_id": payment.id,
                "name": payment.name,
                "amount": payment.amount,
                "date": str(payment.date),
                "partner": payment.partner_id.name,
                "journal": payment.journal_id.name,
                "state": payment.state,
                "moves_paid": [m.name for m in payable],
                "message": f"Payment '{payment.name}' created and posted",
            }

        # Multiple payments created (ungrouped)
        if isinstance(action, dict) and action.get("domain"):
            payments = self.env["account.payment"].search(action["domain"])
        else:
            payments = self.env["account.payment"]

        return {
            "payment_count": len(payments),
            "payments": [
                {
                    "payment_id": p.id,
                    "name": p.name,
                    "amount": p.amount,
                    "partner": p.partner_id.name,
                }
                for p in payments
            ],
            "moves_paid": [m.name for m in payable],
            "message": f"{len(payments)} payment(s) created",
        }
