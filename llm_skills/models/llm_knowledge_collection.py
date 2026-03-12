import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class LLMKnowledgeCollectionSkills(models.Model):
    _inherit = "llm.knowledge.collection"

    @api.model
    def _create_meta_skills_collection(self):
        """
        Called from llm_store_data.xml to create the Odoo Technical Skills collection.
        Idempotent: skips if already exists.
        Resolves the embedding model automatically:
          - prefers text-embedding-3-small
          - falls back to any available embedding model
          - skips with a warning if none found (retry after fetching models)
        """
        existing = self.search([("name", "=", "Odoo Technical Skills")], limit=1)
        if existing:
            _logger.info(
                "llm_skills: 'Odoo Technical Skills' collection already exists (id=%s), skipping.",
                existing.id,
            )
            self._ensure_external_id(existing.id)
            return

        store = self.env.ref("llm_skills.llm_store_pgvector_default", raise_if_not_found=False)
        if not store:
            _logger.warning("llm_skills: pgvector store not found, skipping collection creation.")
            return

        # Resolve embedding model — prefer nomic-embed-text (Ollama local)
        embedding_model = self.env["llm.model"].search(
            [("name", "like", "nomic-embed-text"), ("model_use", "=", "embedding")],
            limit=1,
        )
        if not embedding_model:
            embedding_model = self.env["llm.model"].search(
                [("model_use", "=", "embedding")],
                limit=1,
            )
        if not embedding_model:
            _logger.warning(
                "llm_skills: No embedding model found — skipping 'Odoo Technical Skills' collection creation. "
                "Fetch models from your provider, then call _create_meta_skills_collection() manually "
                "or upgrade the llm_skills module."
            )
            return

        collection = self.create({
            "name": "Odoo Technical Skills",
            "description": (
                "Default knowledge collection for all technical skill documents "
                "loaded from installed addon skills/ directories."
            ),
            "store_id": store.id,
            "embedding_model_id": embedding_model.id,
            "active": True,
        })
        self._ensure_external_id(collection.id)

        _logger.info(
            "llm_skills: Created 'Odoo Technical Skills' collection (id=%s) with embedding model '%s'.",
            collection.id,
            embedding_model.name,
        )

    @api.model
    def _ensure_external_id(self, res_id):
        """Register llm_skills.llm_collection_meta_skills external ID if not present."""
        IrModelData = self.env["ir.model.data"]
        exists = IrModelData.search([
            ("module", "=", "llm_skills"),
            ("name", "=", "llm_collection_meta_skills"),
        ], limit=1)
        if not exists:
            IrModelData.create({
                "name": "llm_collection_meta_skills",
                "module": "llm_skills",
                "model": "llm.knowledge.collection",
                "res_id": res_id,
                "noupdate": True,
            })
