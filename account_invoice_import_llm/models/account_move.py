"""
Account Move Extension for LLM-OCR Processing

Adds "Process with AI" button to draft invoices for manual OCR processing.
"""

from odoo import models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_edi_decoder(self, file_data, new=False):
        decoder = super()._get_edi_decoder(file_data, new=new)
        if decoder:
            # Prefer UBL/Factur-X decoder over LLM parsing, if available.
            return decoder

        # Check if it's a vendor bill with an attachment, from an email alias
        if (
            self.env.context.get("from_alias")
            and self.is_purchase_document(include_receipts=True)
            and file_data["type"] == "pdf"
        ):
            return self._import_invoice_with_llm
        return None

    def _import_invoice_with_llm(self, invoice, file_data, new=False):
        """Populate a vendor bill from an attachment using LLM extraction."""
        pivot_data = self.env["account.invoice.import.ocr"].extract_invoice_data(
            file_data["content"],
            invoice.company_id,
            file_data["attachment"].mimetype or "application/pdf",
        )
        invoice.with_context(skip_is_manually_modified=True)._update_invoice_from_pivot(
            pivot_data
        )
        return True

    def action_process_with_llm(self):
        """Process with AI button - Update existing draft invoice using OCR.

        Returns:
            dict: Action to reload form view with populated data
        """
        self.ensure_one()

        # Validate invoice state
        if self.state != "draft":
            raise UserError(
                "Can only process draft invoices. "
                "This invoice is already posted or cancelled."
            )

        # Find PDF or image attachment
        attachment = self._find_invoice_attachment()
        if not attachment:
            raise UserError(
                "No PDF or image attachment found on this invoice. "
                "Please attach an invoice document first."
            )

        self._import_invoice_with_llm(
            self,
            {
                "attachment": attachment,
                "content": attachment.raw,
            },
        )

        # Reload form view
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def _find_invoice_attachment(self):
        """Find PDF or image attachment on this invoice.

        Returns:
            ir.attachment: First matching attachment, or False
        """
        return self.env["ir.attachment"].search(
            [
                ("res_model", "=", "account.move"),
                ("res_id", "=", self.id),
                (
                    "mimetype",
                    "in",
                    ["application/pdf", "image/png", "image/jpeg", "image/jpg"],
                ),
            ],
            limit=1,
        )

    def _update_invoice_from_pivot(self, pivot_data):
        """Update invoice from OCA pivot format data.

        Reuses OCA's entire create_invoice() flow but uses write() instead of create().

        Args:
            pivot_data (dict): Invoice data in OCA pivot format
        """
        wizard = self.env["account.invoice.import"]
        import_config = {"company": self.company_id}

        # Step 1: Pre-process pivot data (validates, normalizes, adds currency_rec)
        pivot_data = wizard._pre_process_parsed_inv(pivot_data, self.company_id)

        # Step 2: Convert pivot → create vals (handles all complex logic)
        vals = wizard._prepare_create_invoice_vals(pivot_data, import_config)

        # Step 3: Remove fields that shouldn't change on update
        vals.pop("journal_id", None)  # Keep existing journal
        vals.pop("move_type", None)  # Keep existing type
        vals.pop("company_id", None)  # Keep existing company

        # Step 4: Update invoice with prepared vals
        self.write(vals)

        # Step 5: Post-process (handles amount adjustments, tax forcing)
        wizard._post_process_invoice(pivot_data, import_config, self)

        # Step 6: Final business logic hook
        self.env["business.document.import"].post_create_or_update(pivot_data, self)
