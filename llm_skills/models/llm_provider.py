import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

OPENAI_EMBEDDING_MODELS = [
    {"name": "text-embedding-3-small", "default": True},
    {"name": "text-embedding-3-large", "default": False},
    {"name": "text-embedding-ada-002", "default": False},
]


class LLMProvider(models.Model):
    _inherit = "llm.provider"

    @api.model
    def _setup_openai_provider(self):
        """
        Called from llm_provider_data.xml to ensure the OpenAI provider exists
        and that the three standard embedding models are registered.

        Idempotent: finds existing provider by name if already present.
        Registers external IDs so refs work in subsequent data files.
        """
        IrModelData = self.env["ir.model.data"]

        # ── 1. Provider ──────────────────────────────────────────────────────
        provider = self.search([("name", "=ilike", "OpenAI")], limit=1)
        if not provider:
            provider = self.create({
                "name": "OpenAI",
                "service": "openai",
                "active": True,
            })
            _logger.info("llm_skills: Created OpenAI provider (id=%s).", provider.id)
        else:
            _logger.info("llm_skills: OpenAI provider already exists (id=%s), skipping.", provider.id)

        self._ensure_external_id(IrModelData, "llm.provider", provider.id, "llm_provider_openai")

        # ── 2. Publisher ref (from llm_openai module) ─────────────────────────
        publisher = self.env.ref("llm_openai.llm_publisher_openai", raise_if_not_found=False)

        # ── 3. Embedding models ───────────────────────────────────────────────
        LLMModel = self.env["llm.model"]
        for idx, spec in enumerate(OPENAI_EMBEDDING_MODELS):
            model_name = spec["name"]
            xml_id = model_name.replace("-", "_")  # e.g. llm_model_text_embedding_3_small

            model = LLMModel.search([
                ("name", "=", model_name),
                ("provider_id", "=", provider.id),
            ], limit=1)

            if not model:
                vals = {
                    "name": model_name,
                    "provider_id": provider.id,
                    "model_use": "embedding",
                    "default": spec["default"],
                    "active": True,
                }
                if publisher:
                    vals["publisher_id"] = publisher.id
                model = LLMModel.create(vals)
                _logger.info("llm_skills: Created embedding model '%s' (id=%s).", model_name, model.id)
            else:
                _logger.info("llm_skills: Embedding model '%s' already exists (id=%s), skipping.", model_name, model.id)

            self._ensure_external_id(IrModelData, "llm.model", model.id, xml_id)

    @api.model
    def _ensure_external_id(self, IrModelData, model_name, res_id, xml_name):
        """Register an ir.model.data external ID if not already present."""
        existing = IrModelData.search([
            ("module", "=", "llm_skills"),
            ("name", "=", xml_name),
        ], limit=1)
        if not existing:
            IrModelData.create({
                "name": xml_name,
                "module": "llm_skills",
                "model": model_name,
                "res_id": res_id,
                "noupdate": True,
            })
