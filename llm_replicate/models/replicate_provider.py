import replicate

from odoo import api, models


class LLMProvider(models.Model):
    _inherit = "llm.provider"

    @api.model
    def _get_available_services(self):
        services = super()._get_available_services()
        return services + [("replicate", "Replicate")]

    def replicate_get_client(self):
        """Get Replicate client instance"""
        return replicate.Client(api_token=self.api_key)

    def replicate_chat(self, messages, model=None, stream=False):
        """Send chat messages using Replicate"""
        model = self.get_model(model, "chat")

        # Format messages for Replicate
        # Most Replicate models expect a simple prompt string
        prompt = "\n".join(f"{msg['role']}: {msg['content']}" for msg in messages)

        response = self.client.run(model.name, input={"prompt": prompt})

        if not stream:
            # Replicate responses can vary by model, handle common formats
            content = (
                "".join(response)
                if isinstance(response, list) or isinstance(response, tuple)
                else str(response)
            )
            yield {"role": "assistant", "content": content}
        else:
            for chunk in response:
                yield {"role": "assistant", "content": str(chunk)}

    def replicate_embedding(self, texts, model=None):
        """Generate embeddings using Replicate"""
        model = self.get_model(model, "embedding")

        if not isinstance(texts, list):
            texts = [texts]

        response = self.client.run(model.name, input={"sentences": texts})

        # Ensure we return a list of embeddings
        if len(texts) == 1:
            return [response] if not isinstance(response, list) else response
        return response

    def replicate_models(self):
        """List available Replicate models with pagination support"""
        cursor = ...

        while cursor:
            # Get page of results
            page = self.client.models.list(cursor=cursor)

            # Process models in current page
            for model in page.results:
                details = LLMProvider.serialize_model_data(model.dict())
                capabilities = []

                # Infer capabilities from model metadata
                if "chat" in model.id.lower() or "llm" in model.id.lower():
                    capabilities.append("chat")
                if "embedding" in model.id.lower():
                    capabilities.append("embedding")
                if any(
                    kw in model.id.lower() for kw in ["vision", "image", "multimodal"]
                ):
                    capabilities.append("multimodal")

                if not capabilities:
                    capabilities = ["chat"]  # Default capability

                details["capabilities"] = capabilities

                yield {"name": model.id, "details": details}

            # Check if there are more pages
            cursor = page.next
