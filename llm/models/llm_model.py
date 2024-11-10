from odoo import api, fields, models


class LLMModel(models.Model):
    _name = "llm.model"
    _description = "LLM Model"
    _inherit = ["mail.thread"]

    name = fields.Char(required=True)
    provider_id = fields.Many2one("llm.provider", required=True, ondelete="cascade")
    model_use = fields.Selection(
        [
            ("embedding", "Embedding"),
            ("completion", "Completion"),
            ("chat", "Chat"),
            ("multimodal", "Multimodal"),
        ],
        required=True,
    )
    is_default = fields.Boolean(default=False)
    is_active = fields.Boolean(default=True)

    # Model details
    details = fields.Json()
    model_info = fields.Json()
    parameters = fields.Text()
    template = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.is_default:
                # Ensure only one default per provider/use combo
                self.search(
                    [
                        ("provider_id", "=", record.provider_id.id),
                        ("model_use", "=", record.model_use),
                        ("is_default", "=", True),
                        ("id", "!=", record.id),
                    ]
                ).write({"is_default": False})
        return records
