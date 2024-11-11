import ollama

from odoo import models


class OllamaProvider(models.Model):
    _name = "llm.provider.ollama"
    _inherit = "llm.provider.base"
    _client = None

    def get_client(self):
        if not OllamaProvider._client:
            OllamaProvider._client = ollama.Client(host=self.api_base)
        return OllamaProvider._client

    def list_models(self):
        client = self.get_client()
        models = client.list()
        return models.get("models", [])
