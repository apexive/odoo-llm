import requests
from odoo import models
import ollama


class OllamaProvider(models.Model):
    _name = "llm.provider.ollama"
    _inherit = "llm.provider.base"

    def get_client(self):
        if not self._client:
            self._client = ollama.Client(host=self.api_base)
        return self._client

    def list_models(self):
        """Fetch available models from Ollama server"""
        client = self.get_client()
        url = f"{client.base_url}/api/tags"

        response = requests.get(url)
        response.raise_for_status()

        return [
            {"name": model["name"], "details": model}
            for model in response.json().get("models", [])
        ]
