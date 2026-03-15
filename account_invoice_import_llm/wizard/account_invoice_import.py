"""
OCA Invoice Import Wizard Integration

Integrates LLM-OCR extraction into OCA account_invoice_import wizard.
Overrides fallback_parse_pdf_invoice() to extract invoice data when
embedded XML parsers (UBL, Factur-X) fail.
"""

import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class AccountInvoiceImport(models.TransientModel):
    _inherit = "account.invoice.import"

    @api.model
    def fallback_parse_pdf_invoice(self, file_data, company):
        """Fallback parser using LLM-OCR for PDFs without embedded XML."""
        res = super().fallback_parse_pdf_invoice(file_data, company)
        if res:
            return res

        # Don't break OCA flow if our extraction fails
        try:
            return self.env["account.invoice.import.ocr"].extract_invoice_data(
                file_data, company
            )
        except Exception:
            _logger.exception("LLM-OCR extraction failed, skipping")
            return res
