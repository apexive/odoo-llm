import logging
import os

from odoo import api, models

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Ollama
# ---------------------------------------------------------------------------

OLLAMA_EMBEDDING_MODELS_FALLBACK = [
    {"name": "nomic-embed-text:latest", "default": True},
]

OLLAMA_API_BASE_PARAM = "llm_skills.ollama_api_base"
OLLAMA_DEFAULT_HOST = "http://host.docker.internal:11434"

# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------

# Static fallback models registered when the API key is missing or the live
# fetch fails. Covers the main Claude models we always want available.
ANTHROPIC_CHAT_MODELS_FALLBACK = [
    {"name": "claude-sonnet-4-6",        "use": "chat",       "default": True},
    {"name": "claude-opus-4-6",          "use": "multimodal", "default": False},
    {"name": "claude-haiku-4-5-20251001","use": "chat",       "default": False},
]


class LLMProvider(models.Model):
    _inherit = "llm.provider"

    # =========================================================================
    # Ollama
    # =========================================================================

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
        provider = self._get_or_create_ollama_provider(IrModelData)

        fetched = self._fetch_ollama_models(provider)
        if not fetched:
            _logger.warning(
                "llm_skills: Ollama live model fetch failed — registering fallback embedding models."
            )
            self._register_ollama_fallback_models(provider, IrModelData)

        self._register_ollama_embedding_model_external_ids(provider, IrModelData)

    @api.model
    def _get_or_create_ollama_provider(self, IrModelData):
        provider = self.search([("name", "=ilike", "Ollama")], limit=1)
        if not provider:
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
        self._ensure_provider_external_id(IrModelData, provider.id, "llm_provider_ollama")
        return provider

    @api.model
    def _fetch_ollama_models(self, provider):
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
        existing = {m.name: m for m in LLMModel.search([("provider_id", "=", provider.id)])}

        created = updated = 0
        for model_data in models_data:
            details = model_data.get("details", {})
            name = model_data.get("name") or details.get("id")
            if not name:
                continue

            capabilities = details.get("capabilities", ["chat"])
            model_use = provider._determine_model_use(name, capabilities)
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

    @api.model
    def _register_ollama_fallback_models(self, provider, IrModelData):
        LLMModel = self.env["llm.model"]
        publisher = self.env.ref("llm_ollama.llm_publisher_ollama", raise_if_not_found=False)
        for spec in OLLAMA_EMBEDDING_MODELS_FALLBACK:
            name = spec["name"]
            model = LLMModel.search([
                ("name", "=", name), ("provider_id", "=", provider.id),
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

    @api.model
    def _register_ollama_embedding_model_external_ids(self, provider, IrModelData):
        LLMModel = self.env["llm.model"]
        for spec in OLLAMA_EMBEDDING_MODELS_FALLBACK:
            name = spec["name"]
            model = LLMModel.search([
                ("name", "=", name), ("provider_id", "=", provider.id),
            ], limit=1)
            if model:
                xml_id = name.replace("-", "_").replace(":", "_")
                self._ensure_model_external_id(IrModelData, model.id, xml_id)

    # =========================================================================
    # Anthropic
    # =========================================================================

    @api.model
    def _setup_anthropic_provider(self):
        """
        Called from llm_provider_data.xml during install/upgrade.

        Steps (all idempotent):
          1. Find or create the Anthropic provider record
          2. Resolve ANTHROPIC_API_KEY: env var → already on provider record
          3. If API key found, fetch models live from the Anthropic API
          4. If no key / fetch fails, register fallback Claude models statically
          5. Register ir.model.data external IDs for provider + key models

        API key resolution:
          - Set ANTHROPIC_API_KEY in .env / Docker Compose for automatic setup
          - Or enter the key manually on the provider record in the UI
        """
        IrModelData = self.env["ir.model.data"]
        provider = self._get_or_create_anthropic_provider(IrModelData)
        self._resolve_anthropic_api_key(provider)

        if provider.api_key:
            fetched = self._fetch_anthropic_models(provider)
            if not fetched:
                _logger.warning(
                    "llm_skills: Anthropic live model fetch failed — registering fallback models."
                )
                self._register_anthropic_fallback_models(provider, IrModelData)
        else:
            _logger.info(
                "llm_skills: No Anthropic API key found — registering fallback models only. "
                "Set ANTHROPIC_API_KEY in .env or enter it manually on the provider record."
            )
            self._register_anthropic_fallback_models(provider, IrModelData)

        self._register_anthropic_model_external_ids(provider, IrModelData)

    @api.model
    def _get_or_create_anthropic_provider(self, IrModelData):
        provider = self.search([("name", "=ilike", "Anthropic")], limit=1)
        if not provider:
            provider = self.create({
                "name": "Anthropic",
                "service": "anthropic",
                "active": True,
            })
            _logger.info("llm_skills: Created Anthropic provider (id=%s).", provider.id)
        else:
            _logger.info(
                "llm_skills: Anthropic provider already exists (id=%s), skipping create.",
                provider.id,
            )
        self._ensure_provider_external_id(IrModelData, provider.id, "llm_provider_anthropic")
        return provider

    @api.model
    def _resolve_anthropic_api_key(self, provider):
        """
        Resolve the Anthropic API key from (in priority order):
          1. ANTHROPIC_API_KEY environment variable — set in .env / Docker Compose
          2. Already set on the provider record (e.g. entered manually in the UI)

        If found from the env var and not yet on the provider, writes it to the
        provider record so it is visible in the UI.
        """
        env_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if env_key:
            if not provider.api_key:
                provider.sudo().write({"api_key": env_key})
                _logger.info("llm_skills: Set Anthropic API key from ANTHROPIC_API_KEY env var.")
            return env_key

        if provider.api_key:
            _logger.info("llm_skills: Anthropic API key already set on provider.")
            return provider.api_key

        _logger.warning(
            "llm_skills: No Anthropic API key found. "
            "Set ANTHROPIC_API_KEY in .env or enter it manually on the provider record."
        )
        return None

    @api.model
    def _fetch_anthropic_models(self, provider):
        _logger.info("llm_skills: Fetching models from Anthropic API...")
        try:
            models_data = list(provider.list_models())
        except Exception as e:
            _logger.warning("llm_skills: Anthropic model fetch failed: %s", e)
            return False

        if not models_data:
            _logger.warning("llm_skills: Anthropic returned no models.")
            return False

        LLMModel = self.env["llm.model"]
        publisher = self.env.ref("llm_anthropic.llm_publisher_anthropic", raise_if_not_found=False)
        existing = {m.name: m for m in LLMModel.search([("provider_id", "=", provider.id)])}

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
            "llm_skills: Anthropic model sync done — %d created, %d updated.",
            created, updated,
        )
        return (created + updated) > 0

    @api.model
    def _register_anthropic_fallback_models(self, provider, IrModelData):
        LLMModel = self.env["llm.model"]
        publisher = self.env.ref("llm_anthropic.llm_publisher_anthropic", raise_if_not_found=False)
        for spec in ANTHROPIC_CHAT_MODELS_FALLBACK:
            name = spec["name"]
            model = LLMModel.search([
                ("name", "=", name), ("provider_id", "=", provider.id),
            ], limit=1)
            if not model:
                vals = {
                    "name": name,
                    "provider_id": provider.id,
                    "model_use": spec["use"],
                    "default": spec["default"],
                    "active": True,
                }
                if publisher:
                    vals["publisher_id"] = publisher.id
                model = LLMModel.create(vals)
                _logger.info(
                    "llm_skills: Registered fallback Anthropic model '%s' (id=%s).",
                    name, model.id,
                )

    @api.model
    def _register_anthropic_model_external_ids(self, provider, IrModelData):
        LLMModel = self.env["llm.model"]
        for spec in ANTHROPIC_CHAT_MODELS_FALLBACK:
            name = spec["name"]
            model = LLMModel.search([
                ("name", "=", name), ("provider_id", "=", provider.id),
            ], limit=1)
            if model:
                xml_id = name.replace("-", "_")
                self._ensure_model_external_id(IrModelData, model.id, xml_id)

    # =========================================================================
    # Shared helpers
    # =========================================================================

    @api.model
    def _ensure_provider_external_id(self, IrModelData, res_id, xml_name):
        self._ensure_external_id(IrModelData, "llm.provider", res_id, xml_name)

    @api.model
    def _ensure_model_external_id(self, IrModelData, res_id, xml_name):
        self._ensure_external_id(IrModelData, "llm.model", res_id, xml_name)

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
