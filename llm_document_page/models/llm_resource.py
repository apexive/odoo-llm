import logging

from odoo import models

_logger = logging.getLogger(__name__)


class LLMResourceDocumentPage(models.Model):
    """Extend LLMResource to handle document.page model."""

    _inherit = "llm.resource"

    def _get_record_external_url(self, res_model, res_id):
        """
        Extend the external URL computation to handle document.page model.

        :param res_model: The model name
        :param res_id: The record ID
        :return: The external URL or result from super
        """
        # First check if it's a document.page model
        if res_model == "document.page":
            try:
                record = self.env[res_model].browse(res_id)
                if (
                    record.exists()
                    and hasattr(record, "source_url")
                    and record.source_url
                ):
                    return record.source_url
            except Exception as e:
                _logger.warning(
                    "Error computing external URL for document.page resource %s: %s",
                    res_id,
                    str(e),
                )

        # If not a document.page or no URL found, use the standard implementation
        return super()._get_record_external_url(res_model, res_id)
