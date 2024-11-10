from odoo import _, api, fields, models
from odoo.exceptions import UserError


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

    def get_model(self, model=None, model_use="chat"):
        return self.model_ids.filtered(lambda m: m.default and m.model_use == "chat")[0]

    def get_client(self):
        return self._raise_not_implemented("get_client")

    def chat(self, messages, model=None, stream=False):
        return self._raise_not_implemented("chat")

    def embedding(self, texts, model=None):
        return self._raise_not_implemented("embedding")

    def list_models(self):
        return self._raise_not_implemented("list_models")

    def _raise_not_implemented(self, method_name):
        raise NotImplementedError(
            f"Method '{method_name}' not implemented for provider {self.provider}"
        )

    def fetch_models(self):
        """Fetch available models from the provider and create/update them in Odoo"""
        self.ensure_one()

        try:
            models_data = self.list_models()

            created_count = 0
            updated_count = 0

            for model_data in models_data:
                name = model_data.get("name")
                if not name:
                    continue

                # Determine model use based on capabilities
                capabilities = model_data.get("details", {}).get(
                    "capabilities", ["chat"]
                )
                model_use = "chat"  # default
                if "embedding" in capabilities:
                    model_use = "embedding"
                elif "multimodal" in capabilities:
                    model_use = "multimodal"

                # Prepare values for create/update
                values = {
                    "name": name,
                    "provider_id": self.id,
                    "model_use": model_use,
                    "details": model_data.get("details"),
                    "active": True,
                }

                # If model exists, update it
                existing = self.env["llm.model"].search(
                    [("name", "=", name), ("provider_id", "=", self.id)]
                )

                if existing:
                    existing.write(values)
                    updated_count += 1
                else:
                    self.env["llm.model"].create(values)
                    created_count += 1

            # Show success message
            message = _("Successfully fetched models: %d created, %d updated") % (
                created_count,
                updated_count,
            )
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Success"),
                    "message": message,
                    "sticky": False,
                    "type": "success",
                },
            }

        except Exception as e:
            raise UserError(_("Error fetching models: %s") % str(e)) from e
