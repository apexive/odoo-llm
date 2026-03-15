import base64
import logging
import mimetypes
import os
import re

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class LLMResourceParser(models.Model):
    _inherit = "llm.resource"

    llm_model_id = fields.Many2one(
        "llm.model",
        string="OCR Model",
        required=False,
        domain="[('model_use', 'in', ['ocr'])]",
        ondelete="restrict",
    )

    llm_provider_id = fields.Many2one(
        "llm.provider",
        string="Provider",
        domain="[('service', '=', 'mistral')]",
        required=False,
        ondelete="restrict",
    )

    @api.model
    def _get_available_parsers(self):
        parsers = super()._get_available_parsers()
        parsers.extend(
            [
                ("mistral_ocr", "Mistral OCR Parser"),
            ]
        )
        return parsers

    def parse_mistral_ocr(self, record, field):
        """
        Parse the resource content using Mistral OCR.
        """
        mimetype = field["mimetype"]
        if not self.llm_model_id or not self.llm_provider_id:
            raise ValueError("Please select a model and provider.")
        value = field["rawcontent"]
        ocr_response = self.llm_provider_id.process_ocr(
            self.llm_model_id.name, value, mimetype
        )
        final_content = self._format_mistral_ocr_text(ocr_response, record.id)
        self.content = final_content

        return True

    def _format_mistral_ocr_text(self, ocr_response, record_id):
        """Flatten a Mistral OCR response into one big text blob, with page headers."""
        parts = []
        base_stem = f"record_{record_id}"

        for page_idx, page in enumerate(ocr_response.pages, start=1):
            page_md = page.markdown.strip()

            for img in page.images:
                data_uri = img.image_base64 or ""
                if not data_uri:
                    continue

                # split into [ “data:image/jpeg;base64”, “/9j…” ]
                try:
                    header, b64payload = data_uri.split(",", 1)
                except ValueError:
                    _logger.warning("Unexpected image_base64 format: %r", data_uri)
                    continue

                # extract mime type from header: e.g. "data:image/jpeg;base64"
                m = re.match(r"data:([^;]+);base64", header)
                mime = m.group(1) if m else "image/png"
                ext = mimetypes.guess_extension(mime) or ".png"
                img_bytes = base64.b64decode(b64payload)
                orig_id = img.id  # e.g. "img-0.jpeg"
                stem, _ = os.path.splitext(orig_id)
                image_name = f"{base_stem}_p{page_idx}_{stem}{ext}"

                attachment = self.env["ir.attachment"].create(
                    {
                        "name": image_name,
                        "datas": base64.b64encode(img_bytes).decode("ascii"),
                        "res_model": self._name,
                        "res_id": self.id,
                        "mimetype": mime,
                    }
                )

                url = f"/web/image/{attachment.id}/datas"
                pattern = rf"\!\[([^\]]*)\]\(\s*{re.escape(orig_id)}\s*\)"
                replacement = rf"![\1]({url})"
                page_md = re.sub(pattern, replacement, page_md)

            parts.append(f"## Page {page_idx}\n\n{page_md}")

        return "\n\n".join(parts)
