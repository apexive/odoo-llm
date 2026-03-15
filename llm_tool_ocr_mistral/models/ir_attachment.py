import base64
import logging
from typing import List

from odoo import models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.llm_tool.decorators import llm_tool

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    @llm_tool(
        name="llm_tool_ocr_mistral",
        xml_managed=True,  # Tool defined in XML data file, skip auto-registration
    )
    def llm_tool_ocr_mistral(self, attachment_ids: List[int]) -> List[dict]:
        """
        Parse document attachment(s) using Mistral OCR.

        Extracts text content from PDF files and images using Mistral's OCR
        (Optical Character Recognition) vision models.

        Args:
            attachment_ids: List of attachment IDs to parse

        Returns:
            List of dicts, one per attachment: [{
                "attachment_id": int,
                "extracted_text": str,      # Markdown with "## Page N" headers
                "pages": int,
                "attachment_name": str,
                "mimetype": str,
                "error": str                # Only present if parsing failed
            }]

        Raises:
            UserError: If Mistral provider or OCR model not configured

        Examples:
            >>> # Single attachment
            >>> self.env['ir.attachment'].llm_tool_ocr_mistral([123])
            [{
                "attachment_id": 123,
                "extracted_text": "## Page 1\n\nInvoice #12345...",
                "pages": 2,
                "attachment_name": "invoice.pdf",
                "mimetype": "application/pdf"
            }]

            >>> # Multiple attachments
            >>> self.env['ir.attachment'].llm_tool_ocr_mistral([123, 124, 125])
            [
                {"attachment_id": 123, "extracted_text": "...", "pages": 2, ...},
                {"attachment_id": 124, "extracted_text": "...", "pages": 1, ...},
                {"attachment_id": 125, "error": "No content", "pages": 0, ...}
            ]
        """
        # Get provider and model ONCE (not in loop!)
        provider, ocr_model = self._get_mistral_ocr_config()

        # Process all attachments
        results = []
        for att_id in attachment_ids:
            try:
                result = self._parse_attachment(att_id, provider, ocr_model)
                results.append(result)
            except Exception as e:
                # Include error in results, continue processing
                _logger.warning(f"Failed to parse attachment {att_id}: {e}")
                results.append(
                    {
                        "attachment_id": att_id,
                        "error": str(e),
                        "extracted_text": "",
                        "pages": 0,
                    }
                )

        return results

    def _get_mistral_ocr_config(self):
        """
        Get Mistral provider and OCR model configuration.
        Called once per tool invocation, not per attachment.

        Returns:
            tuple: (provider, ocr_model)
        """
        # Get provider
        provider = self.env["llm.provider"].search(
            [("service", "=", "mistral")], limit=1
        )
        if not provider:
            raise UserError(
                "Mistral provider not found. Please configure Mistral AI provider in LLM settings."
            )

        # Delegate to provider's method - single source of truth for OCR model selection
        ocr_model = provider.mistral_get_default_ocr_model()

        return provider, ocr_model

    def _parse_attachment(self, attachment_id, provider, ocr_model):
        """
        Parse a single attachment with already-configured provider and model.

        Args:
            attachment_id (int): Attachment ID to parse
            provider: Mistral provider record
            ocr_model: OCR model record

        Returns:
            dict: Parsed document data
        """
        # Get the attachment
        attachment = self.browse(attachment_id)
        if not attachment.exists():
            raise ValidationError(f"Attachment with ID {attachment_id} not found")

        # Get attachment data
        mimetype = attachment.mimetype or "application/pdf"
        datas = attachment.datas

        if not datas:
            raise ValidationError(f"Attachment '{attachment.name}' has no content")

        # Decode base64 to bytes
        data_bytes = base64.b64decode(datas)

        # Call provider's OCR processing
        ocr_response = provider.process_ocr(
            model_name=ocr_model.name,
            data=data_bytes,
            mimetype=mimetype,
        )

        # Format response to markdown
        extracted_text = self._format_ocr_response(ocr_response)

        return {
            "attachment_id": attachment_id,
            "extracted_text": extracted_text,
            "pages": len(ocr_response.pages) if hasattr(ocr_response, "pages") else 1,
            "attachment_name": attachment.name,
            "mimetype": mimetype,
        }

    def _format_ocr_response(self, ocr_response):
        """
        Format Mistral OCR response into simple markdown text.

        Args:
            ocr_response: Response object from Mistral OCR API

        Returns:
            str: Markdown-formatted text with page headers
        """
        parts = []

        for page_idx, page in enumerate(ocr_response.pages, start=1):
            page_md = page.markdown.strip() if page.markdown else ""
            if page_md:
                parts.append(f"## Page {page_idx}\n\n{page_md}")

        return "\n\n".join(parts) if parts else ""
