from odoo import models
from openai import OpenAI


class OpenAIProvider(models.Model):
    _name = "llm.provider.openai"
    _inherit = "llm.provider.base"
    _client = None

    def get_client(self):
        if not OpenAIProvider._client:
            OpenAIProvider._client = OpenAI(api_key=self.api_key, base_url=self.api_base or None)
            return OpenAIProvider._client

    def chat(self, messages, model=None, stream=False):
        client = self.get_client()
        model = self.get_model(model, "chat")
        response = client.chat.completions.create(
            model=model.name,
            messages=messages,
            stream=stream,
        )
        if not stream:
            return response.choices[0].message
        return response

    def embedding(self, texts, model=None):
        client = self.get_client()
        model = self.get_model(model, "embedding")
        response = client.embeddings.create(model=model.name, input=texts)
        return [r.embedding for r in response.data]

    def list_models(self):
        client = self.get_client()
        models = client.models.list()
        return [
            {"name": model.id, "details": model.model_dump()} for model in models.data
        ]
