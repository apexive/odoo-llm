from odoo import api, fields, models


class LLMProvider(models.Model):
    _name = "llm.provider"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "LLM Provider"

    name = fields.Char(required=True)
    provider = fields.Selection(
        selection="_selection_provider",
        required=True,
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    api_key = fields.Char()
    api_base = fields.Char()
    model_ids = fields.One2many("llm.model", "provider_id", string="Models")

    @api.model
    def _get_available_providers(self):
        """Hook method for adding providers"""
        return [
            ("openai", "OpenAI"),
            ("ollama", "Ollama"),
            ("replicate", "Replicate"),
            ("anthropic", "Anthropic"),
        ]

    @api.model
    def _selection_provider(self):
        return self._get_available_providers()

    def get_client(self):
        return self._raise_not_implemented("get_client")

    def chat(self, messages, stream=False):
        return self._raise_not_implemented("chat")

    def chat_stream(self, messages):
        return self._raise_not_implemented("chat_stream")

    def embedding(self, texts):
        return self._raise_not_implemented("embedding")

    def _raise_not_implemented(self, method_name):
        raise NotImplementedError(
            f"Method '{method_name}' not implemented for provider {self.provider}"
        )
