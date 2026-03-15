import json
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class LLMModel(models.Model):
    _inherit = "llm.model"

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to ensure details field is parsed as dict for FAL.AI models"""
        for vals in vals_list:
            # Check if this is a FAL.AI model by checking the provider
            if vals.get("provider_id"):
                provider = self.env["llm.provider"].browse(vals["provider_id"])
                if provider.service == "fal_ai" and vals.get("details"):
                    # If details is a string, parse it to dict
                    if isinstance(vals["details"], str):
                        try:
                            vals["details"] = json.loads(vals["details"])
                            _logger.info(
                                "Parsed FAL.AI model details from string to dict"
                            )
                        except json.JSONDecodeError as e:
                            _logger.error(
                                f"Failed to parse FAL.AI model details JSON: {e}"
                            )

        return super().create(vals_list)
