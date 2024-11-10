from odoo import _, api, fields, models
from odoo.exceptions import UserError


class LLMProviderBase(models.AbstractModel):
    """Base model for provider implementations"""

    _inherit = ["mail.thread"]
    _name = "llm.provider.base"
    _description = "Base LLM Provider Implementation"

    provider_id = fields.Many2one("llm.provider", required=True, ondelete="cascade")

    _client = None

    @property
    def api_key(self):
        return self.provider_id.api_key

    @property
    def api_base(self):
        return self.provider_id.api_base

    def get_client(self):
        raise NotImplementedError()

    def chat(self, messages, model=None, stream=False):
        print("BASE PROVIDER")
        client = self.get_client()
        model = self.get_model(model, model_use="chat")

        print("PROVIDE")
        print(messages)
        response = client.chat(
            messages=messages,
            stream=stream,
            model=model.name,
        )
        print(response)

        if not stream:
            # For non-streaming, extract the content from the response
            # Handle different provider response formats
            if hasattr(response, "choices") and response.choices:
                # OpenAI-style response
                return response.choices[0].message.content
            elif hasattr(response, "content"):
                # Anthropic-style response
                return response.content[0].text
            elif hasattr(response, "message"):
                return response.message["content"]
            else:
                # Fallback for other formats - convert response to string
                return str(response)
        else:
            # For streaming, yield chunks as they come
            for chunk in response:
                if hasattr(chunk, "choices") and chunk.choices:
                    # OpenAI-style chunks
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                elif hasattr(chunk, "delta"):
                    # Alternative format
                    if chunk.delta:
                        yield chunk.delta
                elif hasattr(chunk, "text"):
                    # Anthropic-style chunks
                    yield chunk.text
                else:
                    # Fallback - convert chunk to string
                    yield str(chunk)

    def embedding(self, texts, model=None):
        client = self.get_client()
        response = client.embeddings(
            model=self.get_model(model, "embedding").name, texts=texts
        )
        return [r["embedding"] for r in response["data"]]

    def get_model(self, model=None, model_use="chat"):
        """Get a model to use for the given purpose

        Args:
            model: Optional specific model to use
            model_use: Type of model to get if no specific model provided

        Returns:
            llm.model record to use
        """
        if model:
            return model

        # Get models from the main provider record
        models = self.provider_id.model_ids

        # Filter for default model of requested type
        default_models = models.filtered(
            lambda m: m.default and m.model_use == model_use
        )

        if not default_models:
            # Fallback to any model of requested type
            default_models = models.filtered(lambda m: m.model_use == model_use)

        if not default_models:
            raise ValueError(
                f"No {model_use} model found for provider {self.provider_id.name}"
            )

        return default_models[0]


class LLMProvider(models.Model):
    _name = "llm.provider"
    _inherit = ["mail.thread"]
    _description = "LLM Provider"

    name = fields.Char(required=True)
    provider = fields.Selection(
        selection="_get_available_providers",
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

    # Reference to provider implementation
    provider_impl_id = fields.Reference(
        selection="_get_provider_models",
        string="Provider Implementation",
        compute="_compute_provider_impl",
        store=True,
    )

    @api.model
    def _get_provider_models(self):
        """Get available provider implementation models"""
        return [
            (f"llm.provider.{provider[0]}", provider[1])
            for provider in self._get_available_providers()
        ]

    @api.model
    def _get_available_providers(self):
        """Hook method for adding providers"""
        return [
            ("openai", "OpenAI"),
            ("ollama", "Ollama"),
            ("replicate", "Replicate"),
            ("anthropic", "Anthropic"),
        ]

    @api.depends("provider")
    def _compute_provider_impl(self):
        """Create/get provider implementation based on provider type"""
        for record in self:
            if not record.provider:
                record.provider_impl_id = False
                continue

            # Map provider to implementation model
            impl_model = f"llm.provider.{record.provider}"

            # Find or create implementation
            impl = self.env[impl_model].search(
                [("provider_id", "=", record.id)], limit=1
            )

            if not impl:
                impl = self.env[impl_model].create(
                    {
                        "provider_id": record.id,
                    }
                )

            record.provider_impl_id = f"{impl_model},{impl.id}"

    def get_client(self):
        return self.provider_impl_id.get_client()

    def chat(self, messages, model=None, stream=False):
        print("IN THE CHAIN")
        print(stream)
        return self.provider_impl_id.chat(messages, model=model, stream=stream)

    def embedding(self, texts, model=None):
        return self.provider_impl_id.embedding(texts, model)

    def list_models(self):
        return self.provider_impl_id.list_models()

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
