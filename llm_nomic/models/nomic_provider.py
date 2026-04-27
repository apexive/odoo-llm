import logging

import requests

from odoo import api, models

_logger = logging.getLogger(__name__)

NOMIC_EMBEDDING_URL = "https://api-atlas.nomic.ai/v1/embedding/text"

# Nomic has no /models discovery endpoint — enumerate known models statically.
NOMIC_KNOWN_MODELS = [
    {"name": "nomic-embed-text-v1.5", "capabilities": ["embedding"]},
    {"name": "nomic-embed-text-v1", "capabilities": ["embedding"]},
    {"name": "nomic-embed-vision-v1.5", "capabilities": ["embedding"]},
    {"name": "nomic-embed-vision-v1", "capabilities": ["embedding"]},
]


class LLMProvider(models.Model):
    _inherit = "llm.provider"

    @api.model
    def _get_available_services(self):
        return super()._get_available_services() + [("nomic", "Nomic")]

    def nomic_models(self, model_id=None):
        """Yield known Nomic models (no discovery API exists)."""
        for m in NOMIC_KNOWN_MODELS:
            if model_id and m["name"] != model_id:
                continue
            yield {"name": m["name"], "details": {"id": m["name"], "capabilities": m["capabilities"]}}

    def nomic_get_client(self):
        """Return a requests.Session pre-configured with the Nomic Bearer token."""
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })
        return session

    def nomic_embedding(self, texts, model=None, task_type="search_document"):
        """Generate embeddings via the Nomic Atlas /v1/embedding/text endpoint.

        Args:
            texts: list of strings to embed
            model: llm.model record (optional, falls back to default embedding model)
            task_type: one of search_document, search_query, classification, clustering

        Returns:
            list of embedding vectors (list of floats)
        """
        model = self.get_model(model, "embedding")

        if isinstance(texts, str):
            texts = [texts]

        payload = {
            "model": model.name,
            "texts": texts,
            "task_type": task_type,
        }

        response = self.client.post(NOMIC_EMBEDDING_URL, json=payload)
        response.raise_for_status()

        data = response.json()
        return data["embeddings"]
