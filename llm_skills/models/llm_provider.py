import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

# Default embedding models to register statically when the Ollama server
# is not reachable at install/upgrade time.
OLLAMA_EMBEDDING_MODELS_FALLBACK = [
    {"name": "nomic-embed-text:latest", "default": True},
]

# System parameter key where the Ollama API base URL is optionally stored.
# Defaults to http://host.docker.internal:11434 when not set.
OLLAMA_API_BASE_PARAM = "llm_skills.ollama_api_base"
OLLAMA_DEFAULT_HOST = "http://host.docker.internal:11434"


class LLMProvider(models.Model):
    _inherit = "llm.provider"

    @api.model
    def _setup_ollama_provider(self):
        """
        Called from llm_provider_data.xml during install/upgrade.

        Steps (all idempotent):
          1. Find or create the Ollama provider record
          2. Set api_base from ir.config_parameter or use the default Docker host
          3. Attempt to fetch models live from the Ollama server
          4. If fetch fails, fall back to registering nomic-embed-text statically
          5. Register ir.model.data external IDs for provider + embedding model

        To override the default Ollama host:
            Settings → Technical → System Parameters → New
            Key:   llm_skills.ollama_api_base
            Value: http://host.docker.internal:11434
        """
        IrModelData = self.env["ir.model.data"]

        # ── 1. Provider ───────────────────────────────────────────────────────
        provider = self._get_or_create_ollama_provider(IrModelData)

        # ── 2. Fetch models (live or fallback) ────────────────────────────────
        fetched = self._fetch_ollama_models(provider)
        if not fetched:
            _logger.warning(
                "llm_skills: Ollama live model fetch failed — registering fallback embedding models."
            )
            self._register_fallback_embedding_models(provider, IrModelData)

        # ── 3. Register external IDs for key embedding models ─────────────────
        self._register_embedding_model_external_ids(provider, IrModelData)

    # -------------------------------------------------------------------------
    # Provider setup
    # -------------------------------------------------------------------------

    @api.model
    def _get_or_create_ollama_provider(self, IrModelData):
        """Find or create the Ollama provider. Returns the provider record."""
        provider = self.search([("name", "=ilike", "Ollama")], limit=1)
        if not provider:
            # Resolve api_base: system parameter → default Docker host
            IrConfigParam = self.env["ir.config_parameter"].sudo()
            api_base = (
                IrConfigParam.get_param(OLLAMA_API_BASE_PARAM, "").strip()
                or OLLAMA_DEFAULT_HOST
            )
            provider = self.create({
                "name": "Ollama",
                "service": "ollama",
                "api_base": api_base,
                "active": True,
            })
            _logger.info(
                "llm_skills: Created Ollama provider (id=%s) with api_base='%s'.",
                provider.id, api_base,
            )
        else:
            _logger.info(
                "llm_skills: Ollama provider already exists (id=%s), skipping create.",
                provider.id,
            )
        self._ensure_external_id(IrModelData, "llm.provider", provider.id, "llm_provider_ollama")
        return provider

    # -------------------------------------------------------------------------
    # Live model fetching
    # -------------------------------------------------------------------------

    @api.model
    def _fetch_ollama_models(self, provider):
        """
        Fetch models from the running Ollama server and upsert llm.model records.
        Only registers models whose name contains 'embed' as embedding models;
        all others default to 'chat'.

        Returns True if at least one model was created/updated, False otherwise.
        """
        _logger.info("llm_skills: Fetching models from Ollama server at '%s'...", provider.api_base)
        try:
            models_data = list(provider.list_models())
        except Exception as e:
            _logger.warning("llm_skills: Ollama model fetch failed: %s", e)
            return False

        if not models_data:
            _logger.warning("llm_skills: Ollama returned no models.")
            return False

        LLMModel = self.env["llm.model"]
        publisher = self.env.ref("llm_ollama.llm_publisher_ollama", raise_if_not_found=False)
        existing = {
            m.name: m
            for m in LLMModel.search([("provider_id", "=", provider.id)])
        }

        created = updated = 0
        for model_data in models_data:
            details = model_data.get("details", {})
            name = model_data.get("name") or details.get("id")
            if not name:
                continue

            capabilities = details.get("capabilities", ["chat"])
            model_use = provider._determine_model_use(name, capabilities)

            # Mark as default embedding model if it's nomic-embed-text
            is_default = "nomic-embed-text" in name and model_use == "embedding"

            vals = {
                "name": name,
                "provider_id": provider.id,
                "model_use": model_use,
                "details": details,
                "active": True,
            }
            if is_default:
                vals["default"] = True
            if publisher:
                vals["publisher_id"] = publisher.id

            if name in existing:
                existing[name].write(vals)
                updated += 1
            else:
                LLMModel.create(vals)
                created += 1

        _logger.info(
            "llm_skills: Ollama model sync done — %d created, %d updated.",
            created, updated,
        )
        return (created + updated) > 0

    # -------------------------------------------------------------------------
    # Fallback static registration
    # -------------------------------------------------------------------------

    @api.model
    def _register_fallback_embedding_models(self, provider, IrModelData):
        """Register nomic-embed-text statically without a live Ollama call."""
        LLMModel = self.env["llm.model"]
        publisher = self.env.ref("llm_ollama.llm_publisher_ollama", raise_if_not_found=False)

        for spec in OLLAMA_EMBEDDING_MODELS_FALLBACK:
            name = spec["name"]
            model = LLMModel.search([
                ("name", "=", name),
                ("provider_id", "=", provider.id),
            ], limit=1)
            if not model:
                vals = {
                    "name": name,
                    "provider_id": provider.id,
                    "model_use": "embedding",
                    "default": spec["default"],
                    "active": True,
                }
                if publisher:
                    vals["publisher_id"] = publisher.id
                model = LLMModel.create(vals)
                _logger.info(
                    "llm_skills: Registered fallback embedding model '%s' (id=%s).",
                    name, model.id,
                )

    # -------------------------------------------------------------------------
    # External ID registration
    # -------------------------------------------------------------------------

    @api.model
    def _register_embedding_model_external_ids(self, provider, IrModelData):
        """Register ir.model.data external IDs for the key embedding models."""
        LLMModel = self.env["llm.model"]
        for spec in OLLAMA_EMBEDDING_MODELS_FALLBACK:
            name = spec["name"]
            model = LLMModel.search([
                ("name", "=", name),
                ("provider_id", "=", provider.id),
            ], limit=1)
            if model:
                # e.g. nomic-embed-text:latest → nomic_embed_text_latest
                xml_id = name.replace("-", "_").replace(":", "_")
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
