import requests

from odoo import models


class OllamaProvider(models.Model):
    _name = "llm.provider.ollama"
    _inherit = "llm.provider.base"

    def get_client(self):
        class OllamaClient:
            def __init__(self, base_url):
                self.base_url = base_url or "http://localhost:11434"

            def chat_completions(self, model, messages, stream=False):
                url = f"{self.base_url}/api/chat"
                data = {"model": model, "messages": messages, "stream": stream}

                response = requests.post(url, json=data, stream=stream)
                response.raise_for_status()

                if not stream:
                    return response.json()
                return response.iter_lines()

            def embeddings(self, model, texts):
                url = f"{self.base_url}/api/embeddings"
                data = {"model": model, "texts": texts}

                response = requests.post(url, json=data)
                response.raise_for_status()
                return response.json()

        return OllamaClient(base_url=self.api_base)

    def chat(self, messages, model=None, stream=False):
        client = self.get_client()
        model = self.get_model(model, "chat")
        response = client.chat_completions(
            model=model.name, messages=messages, stream=stream
        )

        if not stream:
            return response["message"]["content"]
        return response

    def embedding(self, texts, model=None):
        client = self.get_client()
        model = self.get_model(model, "embedding")
        response = client.embeddings(model=model.name, texts=texts)
        return [r["embedding"] for r in response["data"]]

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
