from odoo import models


class AnthropicProvider(models.Model):
    _name = "llm.provider.anthropic"
    _inherit = "llm.provider.base"

    def get_client(self):
        from anthropic import Anthropic

        return Anthropic(api_key=self.api_key)

    # def chat(self, messages, model=None, stream=False):
    #     client = self.get_client()
    #     model = self.get_model(model, "chat")
    #
    #     # Convert messages to Anthropic format
    #     formatted_messages = []
    #     for msg in messages:
    #         if msg["role"] == "user":
    #             formatted_messages.append({"role": "user", "content": msg["content"]})
    #         elif msg["role"] == "assistant":
    #             formatted_messages.append(
    #                 {"role": "assistant", "content": msg["content"]}
    #             )
    #         elif msg["role"] == "system":
    #             # Anthropic handles system messages differently - prepend to first user message
    #             if formatted_messages and formatted_messages[0]["role"] == "user":
    #                 formatted_messages[0]["content"] = (
    #                     f"{msg['content']}\n\n{formatted_messages[0]['content']}"
    #                 )
    #             else:
    #                 formatted_messages.append(
    #                     {"role": "user", "content": msg["content"]}
    #                 )
    #
    #     response = client.messages.create(
    #         model=model.name, messages=formatted_messages, stream=stream
    #     )
    #
    #     if not stream:
    #         return response.content[0].text
    #     return response

    def embedding(self, texts, model=None):
        client = self.get_client()
        model = self.get_model(model, "embedding")
        response = client.embeddings.create(model=model.name, input=texts)
        return [r.embedding for r in response.data]

    def list_models(self):
        """List available Anthropic models"""
        # Anthropic doesn't have an API endpoint for listing models
        # Return hardcoded list of known models
        return [
            {
                "name": "claude-3-opus-20240229",
                "details": {
                    "id": "claude-3-opus-20240229",
                    "type": "chat",
                    "capabilities": ["chat", "multimodal"],
                },
            },
            {
                "name": "claude-3-sonnet-20240229",
                "details": {
                    "id": "claude-3-sonnet-20240229",
                    "type": "chat",
                    "capabilities": ["chat", "multimodal"],
                },
            },
            {
                "name": "claude-3-haiku-20240307",
                "details": {
                    "id": "claude-3-haiku-20240307",
                    "type": "chat",
                    "capabilities": ["chat", "multimodal"],
                },
            },
            {
                "name": "claude-2.1",
                "details": {
                    "id": "claude-2.1",
                    "type": "chat",
                    "capabilities": ["chat"],
                },
            },
        ]
