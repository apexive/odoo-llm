import logging
import os

from odoo import api, models

_logger = logging.getLogger(__name__)

# Fallback embedding models registered when no API key is available
# or when the live fetch fails. These cover the models we always want.
OPENAI_EMBEDDING_MODELS_FALLBACK = [
    {"name": "text-embedding-3-small", "default": True},
    {"name": "text-embedding-3-large", "default": False},
    {"name": "text-embedding-ada-002", "default": False},
]

# System parameter key where the OpenAI API key is stored.
# Set this via Settings → Technical → System Parameters before install/upgrade
# to enable automatic model fetching.
OPENAI_API_KEY_PARAM = "llm_skills.openai_api_key"


class LLMProvider(models.Model):
    _inherit = "llm.provider"

    @api.model
    def _setup_openai_provider(self):
        """
        Called from llm_provider_data.xml during install/upgrade.

        Steps (all idempotent):
          1. Find or create the OpenAI provider record
          2. If an API key is stored in ir.config_parameter, set it on the provider
             and fetch all models live from the OpenAI API
          3. If no API key / fetch fails, fall back to registering the three
             standard embedding models statically
          4. Register ir.model.data external IDs for provider + key models

        To enable automatic fetching:
            Settings → Technical → System Parameters → New
            Key:   llm_skills.openai_api_key
            Value: sk-...
        """
        IrModelData = self.env["ir.model.data"]

        # ── 1. Provider ───────────────────────────────────────────────────────
        provider = self._get_or_create_openai_provider(IrModelData)

        # ── 2. API key: env var → system parameter → already on provider ────────
        api_key = self._resolve_openai_api_key(provider)

        # ── 3. Fetch models (live or fallback) ────────────────────────────────
        if provider.api_key:
            fetched = self._fetch_openai_models(provider)
            if not fetched:
                _logger.warning(
                    "llm_skills: Live model fetch failed — registering fallback embedding models."
                )
                self._register_fallback_embedding_models(provider, IrModelData)
        else:
            _logger.info(
                "llm_skills: No OpenAI API key found (set '%s' in system parameters). "
                "Registering fallback embedding models only.",
                OPENAI_API_KEY_PARAM,
            )
            self._register_fallback_embedding_models(provider, IrModelData)

        # ── 4. Register external IDs for key embedding models ─────────────────
        self._register_embedding_model_external_ids(provider, IrModelData)

    # -------------------------------------------------------------------------
    # Provider setup
    # -------------------------------------------------------------------------

    @api.model
    def _get_or_create_openai_provider(self, IrModelData):
        """Find or create the OpenAI provider. Returns the provider record."""
        provider = self.search([("name", "=ilike", "OpenAI")], limit=1)
        if not provider:
            provider = self.create({
                "name": "OpenAI",
                "service": "openai",
                "active": True,
            })
            _logger.info("llm_skills: Created OpenAI provider (id=%s).", provider.id)
        else:
            _logger.info(
                "llm_skills: OpenAI provider already exists (id=%s), skipping create.",
                provider.id,
            )
        self._ensure_external_id(IrModelData, "llm.provider", provider.id, "llm_provider_openai")
        return provider

    @api.model
    def _resolve_openai_api_key(self, provider):
        """
        Resolve the OpenAI API key from multiple sources (priority order):
          1. OPENAI_API_KEY environment variable (set via .env / Docker Compose)
          2. ir.config_parameter key 'llm_skills.openai_api_key'
          3. Already set on the provider record (no action needed)

        If a key is found from env or system params and not yet on the provider,
        it is written to the provider and also stored in ir.config_parameter
        so it survives container restarts without the env var.

        Returns the resolved api_key string, or None if not found.
        """
        IrConfigParam = self.env["ir.config_parameter"].sudo()

        # Source 1: environment variable
        env_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if env_key:
            if not provider.api_key:
                provider.sudo().write({"api_key": env_key})
                _logger.info("llm_skills: Set OpenAI API key from OPENAI_API_KEY env var.")
            # Always sync to ir.config_parameter so it persists
            IrConfigParam.set_param(OPENAI_API_KEY_PARAM, env_key)
            return env_key

        # Source 2: ir.config_parameter
        param_key = IrConfigParam.get_param(OPENAI_API_KEY_PARAM, "").strip()
        if param_key:
            if not provider.api_key:
                provider.sudo().write({"api_key": param_key})
                _logger.info("llm_skills: Set OpenAI API key from ir.config_parameter.")
            return param_key

        # Source 3: already on the provider
        if provider.api_key:
            _logger.info("llm_skills: OpenAI API key already set on provider.")
            return provider.api_key

        _logger.warning(
            "llm_skills: No OpenAI API key found. "
            "Set OPENAI_API_KEY in .env or '%s' in system parameters.",
            OPENAI_API_KEY_PARAM,
        )
        return None

    # -------------------------------------------------------------------------
    # Live model fetching
    # -------------------------------------------------------------------------

    @api.model
    def _fetch_openai_models(self, provider):
        """
        Fetch all models from the OpenAI API and upsert llm.model records.

        Returns True if at least one model was successfully created/updated,
        False if the fetch failed entirely.
        """
        _logger.info("llm_skills: Fetching models from OpenAI API...")
        try:
            models_data = list(provider.list_models())
        except Exception as e:
            _logger.warning("llm_skills: OpenAI model fetch failed: %s", e)
            return False

        if not models_data:
            _logger.warning("llm_skills: OpenAI returned no models.")
            return False

        LLMModel = self.env["llm.model"]
        publisher = self.env.ref("llm_openai.llm_publisher_openai", raise_if_not_found=False)
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

            vals = {
                "name": name,
                "provider_id": provider.id,
                "model_use": model_use,
                "details": details,
                "active": True,
            }
            if publisher:
                vals["publisher_id"] = publisher.id

            if name in existing:
                existing[name].write(vals)
                updated += 1
            else:
                LLMModel.create(vals)
                created += 1

        _logger.info(
            "llm_skills: OpenAI model sync done — %d created, %d updated.",
            created, updated,
        )
        return (created + updated) > 0

    # -------------------------------------------------------------------------
    # Fallback static registration
    # -------------------------------------------------------------------------

    @api.model
    def _register_fallback_embedding_models(self, provider, IrModelData):
        """Register the three standard OpenAI embedding models without an API call."""
        LLMModel = self.env["llm.model"]
        publisher = self.env.ref("llm_openai.llm_publisher_openai", raise_if_not_found=False)

        for spec in OPENAI_EMBEDDING_MODELS_FALLBACK:
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
        for spec in OPENAI_EMBEDDING_MODELS_FALLBACK:
            name = spec["name"]
            model = LLMModel.search([
                ("name", "=", name),
                ("provider_id", "=", provider.id),
            ], limit=1)
            if model:
                xml_id = name.replace("-", "_")  # e.g. text_embedding_3_small
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
