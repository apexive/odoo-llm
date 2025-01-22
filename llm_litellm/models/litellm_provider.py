from odoo import api, models

from .http_client import LiteLLMClient


class LLMProvider(models.Model):
    _inherit = "llm.provider"

    @api.model
    def _get_available_services(self):
        services = super()._get_available_services()
        return services + [("litellm", "LiteLLM Proxy")]

    def litellm_get_client(self):
        """Get LiteLLM client instance"""
        return LiteLLMClient(
            api_key=self.api_key,
            api_base=self.api_base,
        )

    def litellm_chat(self, messages, model=None, stream=False):
        """Send chat messages using LiteLLM proxy"""
        model = self.get_model(model, "chat")

        # Send chat request
        response = self.client.chat_completion(
            messages=messages, model=model.name, stream=stream
        )

        if not stream:
            choice = response["choices"][0]["message"]
            yield {"role": choice["role"], "content": choice["content"]}
        else:
            for chunk in response:
                delta = chunk["choices"][0].get("delta", {})
                if "content" in delta and delta["content"]:
                    yield {"role": "assistant", "content": delta["content"]}

    def litellm_embedding(self, texts, model=None):
        """Generate embeddings using LiteLLM proxy"""
        model = self.get_model(model, "embedding")

        response = self.client.create_embeddings(texts=texts, model=model.name)
        return [data["embedding"] for data in response["data"]]

    def litellm_models(self):
        """List available LiteLLM models"""
        response = self.client.list_models()

        for model in response.get("data", []):
            model_id = model.get("id")
            if not model_id:
                continue

            # Determine capabilities from model properties
            capabilities = ["chat"]  # Default capability
            if "embed" in model_id.lower():
                capabilities = ["embedding"]
            elif any(
                kw in model_id.lower() for kw in ["vision", "image", "multimodal"]
            ):
                capabilities = ["chat", "multimodal"]

            yield {
                "name": model_id,
                "details": {
                    "id": model_id,
                    "capabilities": capabilities,
                    "owned_by": model.get("owned_by"),
                    "permissions": model.get("permission", []),
                },
            }
