from odoo import api, fields, models

MODEL_USE = [
    ("embedding", "Embedding"),
    ("completion", "Completion"),
    ("chat", "Chat"),
    ("multimodal", "Multimodal"),
]


class LLMModel(models.Model):
    _name = "llm.model"
    _description = "LLM Model"
    _inherit = ["mail.thread"]

    name = fields.Char(required=True)
    provider_id = fields.Many2one("llm.provider", required=True, ondelete="cascade")
    model_use = fields.Selection(
        MODEL_USE,
        required=True,
    )
    default = fields.Boolean(default=False)
    active = fields.Boolean(default=True)

    # Model details
    details = fields.Json()
    model_info = fields.Json()
    parameters = fields.Text()
    template = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.default:
                # Ensure only one default per provider/use combo
                self.search(
                    [
                        ("provider_id", "=", record.provider_id.id),
                        ("model_use", "=", record.model_use),
                        ("default", "=", True),
                        ("id", "!=", record.id),
                    ]
                ).write({"default": False})
        return records

    def chat(self, messages, stream=False):
        """Send chat messages using this model"""
        return self.provider_id.chat(messages, model=self, stream=stream)

    def embedding(self, texts):
        """Generate embeddings using this model"""
        return self.provider_id.embedding(texts, model=self)

