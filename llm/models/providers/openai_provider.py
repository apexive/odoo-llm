from odoo import models


class OpenAIProvider(models.Model):
    _inherit = "llm.provider"

    def get_client(self):
        if self.provider != "openai":
            return super().get_client()
        from openai import OpenAI

        return OpenAI(api_key=self.api_key, base_url=self.api_base or None)

    def chat(self, messages, stream=False):
        client = self.get_client()
        response = client.chat.completions.create(
            model=self.model_ids.filtered(
                lambda m: m.is_default and m.model_use == "chat"
            )[0].name,
            messages=messages,
            stream=stream,
        )
        if not stream:
            return response.choices[0].message.content
        return response

    def embedding(self, texts):
        client = self.get_client()
        model = self.model_ids.filtered(
            lambda m: m.is_default and m.model_use == "embedding"
        )[0]
        response = client.embeddings.create(model=model.name, input=texts)
        return [r.embedding for r in response.data]
