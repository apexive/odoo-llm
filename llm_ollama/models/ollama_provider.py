import datetime

import ollama

from odoo import api, models


class LLMProvider(models.Model):
    _inherit = "llm.provider"

    @api.model
    def _get_available_services(self):
        services = super()._get_available_services()
        return services + [("ollama", "Ollama")]

    def ollama_get_client(self):
        """Get Ollama client instance"""
        return ollama.Client(host=self.api_base or "http://localhost:11434")

    def ollama_chat(self, messages, model=None, stream=False, **kwargs):
        """Send chat messages using Ollama"""
        model = self.get_model(model, "chat")

        # Ollama expects a different message format
        formatted_messages = []
        for msg in messages:
            if msg["role"] == "user":
                formatted_messages.append({"role": "user", "content": msg["content"]})
            elif msg["role"] == "assistant":
                formatted_messages.append(
                    {"role": "assistant", "content": msg["content"]}
                )
            elif msg["role"] == "system":
                formatted_messages.append({"role": "system", "content": msg["content"]})

        # Send chat request
        response = self.client.chat(
            model=model.name,
            messages=formatted_messages,
            stream=stream,
        )

        if not stream:
            yield {"role": "assistant", "content": response["message"]["content"]}
        else:
            for chunk in response:
                if "message" in chunk:
                    yield {"role": "assistant", "content": chunk["message"]["content"]}

    def ollama_embedding(self, texts, model=None):
        """Generate embeddings using Ollama"""
        model = self.get_model(model, "embedding")

        # Ensure texts is a list
        if isinstance(texts, str):
            texts = [texts]

        # Get embeddings for each text
        embeddings = []
        for text in texts:
            response = self.client.embeddings(model=model.name, prompt=text)
            embeddings.append(response["embedding"])

        return embeddings

    def ollama_models(self):
        """List available Ollama models"""
        response = self.client.list()

        for model in response.get("models", []):
            # Basic model info
            model_info = {
                "name": model.get("model", ""),
                "details": {
                    "id": model.get("model", ""),
                    "capabilities": ["chat"],  # Default capability
                    "modified_at": model.get("modified_at").strftime(
                        "%Y-%m-%dT%H:%M:%S.%fZ"
                    )
                    if isinstance(model.get("modified_at"), datetime)
                    else model.get("modified_at"),
                    "size": model.get("size"),
                    "digest": model.get("digest"),
                },
            }

            # Add embedding capability if model name suggests it
            if "embedding" in model["model"].lower():
                model_info["details"]["capabilities"].append("embedding")

            yield model_info
