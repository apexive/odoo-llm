from datetime import datetime

from odoo import models


def serialize_datetime(obj):
    """Helper function to serialize datetime objects to ISO format strings."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


def serialize_model_data(data: dict) -> dict:
    """
    Recursively process dictionary to serialize datetime objects
    and handle any other non-serializable types.
    """
    return {
        key: serialize_datetime(value)
        if isinstance(value, datetime)
        else serialize_model_data(value)
        if isinstance(value, dict)
        else [
            serialize_model_data(item)
            if isinstance(item, dict)
            else serialize_datetime(item)
            for item in value
        ]
        if isinstance(value, list)
        else value
        for key, value in data.items()
    }


class ReplicateProvider(models.Model):
    _name = "llm.provider.replicate"
    _inherit = "llm.provider.base"

    def get_client(self):
        import replicate

        return replicate.Client(api_token=self.api_key)

    # def chat(self, messages, model=None, stream=False):
    #     client = self.get_client()
    #     model = self.get_model(model, "chat")
    #
    #     # Format messages for Replicate
    #     # Most Replicate models expect a simple prompt string
    #     prompt = "\n".join(f"{msg['role']}: {msg['content']}" for msg in messages)
    #
    #     response = client.run(model.name, input={"prompt": prompt})
    #
    #     if not stream:
    #         # Replicate responses can vary by model, handle common formats
    #         if isinstance(response, list) or isinstance(response, tuple):
    #             return "".join(response)
    #         return str(response)
    #     return response

    def embedding(self, texts, model=None):
        client = self.get_client()
        model = self.get_model(model, "embedding")

        if not isinstance(texts, list):
            texts = [texts]

        response = client.run(model.name, input={"sentences": texts})

        # Ensure we return a list of embeddings
        if len(texts) == 1:
            return [response] if not isinstance(response, list) else response
        return response

    def list_models(self):
        """Fetch all available models from Replicate, handling pagination"""
        client = self.get_client()
        all_models = []

        # Get first page
        page = False

        while page is False or page.next:
            page = client.models.list()
            all_models.extend(
                [
                    {"name": model.id, "details": serialize_model_data(model.dict())}
                    for model in page.results
                ]
            )

        return all_models
