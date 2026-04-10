from odoo import api, models


class LLMModel(models.Model):
    _inherit = "llm.model"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._auto_generate_transcription_schema()
        return records

    def write(self, vals):
        result = super().write(vals)
        if "details" in vals or "model_use" in vals:
            self._auto_generate_transcription_schema()
        return result

    def _auto_generate_transcription_schema(self):
        for record in self:
            if record.model_use != "transcription":
                continue
            if not record.provider_id:
                continue
            if not record.provider_id.should_generate_transcription_schema(record):
                continue
            record.provider_id.generate_transcription_schema(record)
