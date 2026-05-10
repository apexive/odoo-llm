from odoo import api, models


class LLMModel(models.Model):
    _inherit = "llm.model"

    @api.model
    def _get_available_model_usages(self):
        available_model_usages = super()._get_available_model_usages()
        return available_model_usages + [
            ("ocr", "OCR"),
        ]
