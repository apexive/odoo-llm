# Copyright 2026 Lijo Antony
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html).

import math

import requests

from odoo import _, api, models
from odoo.exceptions import UserError

JEV_SERVICE = "jev"
JEV_SERVICE_LABEL = "TypeSafe Jev"
JEV_MODEL_USE = "decision"
JEV_DEFAULT_MODEL = "jev-1.14.0"
JEV_DEFAULT_API_BASE = "https://api.typesafe.ai"
JEV_SYSTEMONE_PATH = "/v1/systemone"
JEV_DEFAULT_TIMEOUT = 5.0


class JevClient:
    """Lightweight HTTP client for the TypeSafe Jev SystemOne decision API.

    Wraps ``requests.post`` against ``POST /v1/systemone`` with a short request
    timeout and never exposes the bearer API key in string representations.
    """

    def __init__(
        self,
        api_key,
        api_base=None,
        timeout=JEV_DEFAULT_TIMEOUT,
    ):
        self._api_key = api_key
        self.api_base = (api_base or JEV_DEFAULT_API_BASE).rstrip("/")
        self.timeout = timeout

    def __repr__(self):
        return f"<JevClient api_base={self.api_base!r} timeout={self.timeout!r}>"

    @property
    def endpoint(self):
        """Return the full SystemOne endpoint URL."""
        if self.api_base.endswith(JEV_SYSTEMONE_PATH):
            return self.api_base
        if self.api_base.endswith("/v1"):
            return f"{self.api_base}/systemone"
        return f"{self.api_base}{JEV_SYSTEMONE_PATH}"

    def _headers(self):
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def post_systemone(self, payload, timeout=None):
        """Send a typed decision payload to ``POST /v1/systemone``."""
        req_timeout = self.timeout if timeout is None else timeout
        return requests.post(
            self.endpoint,
            json=payload,
            headers=self._headers(),
            timeout=req_timeout,
        )


class LLMModel(models.Model):
    _inherit = "llm.model"

    @api.model
    def _get_available_model_usages(self):
        available_model_usages = super()._get_available_model_usages()
        return available_model_usages + [
            (JEV_MODEL_USE, "Decision"),
        ]


class LLMProvider(models.Model):
    _inherit = "llm.provider"

    @api.model
    def _get_available_services(self):
        """Register TypeSafe Jev as an available LLM provider service."""
        services = super()._get_available_services()
        return services + [(JEV_SERVICE, JEV_SERVICE_LABEL)]

    def _determine_model_use(self, name, capabilities):
        """Classify TypeSafe Jev models under the ``decision`` model use."""
        if self.service == JEV_SERVICE or any(
            cap in (capabilities or []) for cap in [JEV_MODEL_USE]
        ):
            return JEV_MODEL_USE
        return super()._determine_model_use(name, capabilities)

    def jev_get_client(self):
        """Return a configured ``JevClient`` instance for this provider."""
        self.ensure_one()
        api_key = (self.api_key or "").strip()
        if not api_key:
            raise UserError(_("API key is required for TypeSafe Jev provider."))
        return JevClient(
            api_key=api_key,
            api_base=self.api_base,
            timeout=JEV_DEFAULT_TIMEOUT,
        )

    def decide(self, state, predicates, model=None, **kwargs):
        """Dispatch a typed decision evaluation to the active provider service."""
        return self._dispatch(
            "decide",
            state,
            predicates,
            model=model,
            **kwargs,
        )

    def jev_decide(self, state, predicates, model=None, timeout=None):
        """Evaluate typed ``noul`` decision predicates against structured state.

        Builds and posts a ``POST https://api.typesafe.ai/v1/systemone`` request:
        ``{"model": <model_name>, "state": state, "questions": questions}``
        and parses the ``answers`` block into a dict mapping each predicate key
        to its float probability (``noul`` score in ``[0.0, 1.0]``).

        Args:
            state (dict): Structured JSON evidence dictionary evaluated by Jev.
            predicates (dict | list): Mapping of predicate key -> question spec
                (``{"type": "noul", "instructions": "...", "criteria": {...}}``
                or instruction string), or a list of predicate dicts carrying
                ``name`` and ``instructions``.
            model (llm.model | str | None): Optional model record or model name.
                Defaults to the provider's default model or ``jev-1.14.0``.
            timeout (float | None): Request timeout in seconds (defaults to 5.0s).

        Returns:
            dict[str, float]: Mapping of predicate key -> probability.
        """
        self.ensure_one()
        if not isinstance(state, dict) or not state:
            raise UserError(
                _(
                    "A non-empty state dictionary is required for TypeSafe Jev decisions."
                )
            )

        questions = self._jev_normalize_predicates(predicates)
        model_name = self._jev_resolve_model_name(model)
        req_timeout = self._jev_validate_timeout(timeout)
        client = self.jev_get_client()

        payload = {
            "model": model_name,
            "state": state,
            "questions": questions,
        }

        try:
            response = client.post_systemone(payload, timeout=req_timeout)
        except requests.exceptions.Timeout:
            raise UserError(
                _(
                    "TypeSafe Jev API request timed out after %(timeout)s seconds "
                    "(status: timeout)."
                )
                % {"timeout": req_timeout}
            ) from None
        except requests.exceptions.HTTPError as exc:
            status_code = (
                getattr(getattr(exc, "response", None), "status_code", None)
                or "http_error"
            )
            raise UserError(
                _("TypeSafe Jev API request failed with HTTP status %(status)s.")
                % {"status": status_code}
            ) from None
        except requests.exceptions.RequestException as exc:
            status_code = (
                getattr(getattr(exc, "response", None), "status_code", None)
                or "connection_error"
            )
            raise UserError(
                _("TypeSafe Jev API request failed (status: %(status)s).")
                % {"status": status_code}
            ) from None

        if response.status_code != 200:
            raise UserError(
                _("TypeSafe Jev API request failed with HTTP status %(status)s.")
                % {"status": response.status_code}
            )

        try:
            response_json = response.json()
        except ValueError:
            raise UserError(
                _(
                    "TypeSafe Jev API returned non-JSON content "
                    "(HTTP status %(status)s)."
                )
                % {"status": response.status_code}
            ) from None

        return self._jev_parse_answers(
            response_json,
            expected_keys=tuple(questions.keys()),
            status_code=response.status_code,
        )

    @api.model
    def _jev_validate_timeout(self, timeout):
        """Require a finite positive timeout before transport starts."""
        if timeout is None:
            return JEV_DEFAULT_TIMEOUT
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
            raise UserError(_("The Jev timeout must be a finite positive number."))
        try:
            value = float(timeout)
        except (TypeError, ValueError, OverflowError):
            raise UserError(
                _("The Jev timeout must be a finite positive number.")
            ) from None
        if not math.isfinite(value) or value <= 0:
            raise UserError(_("The Jev timeout must be a finite positive number."))
        return value

    def _jev_resolve_model_name(self, model=None):
        """Select an active decision model or accept an explicit service name."""
        if model is not None:
            if isinstance(model, str) and model.strip():
                return model.strip()
            if (
                isinstance(model, models.BaseModel)
                and model._name == "llm.model"
                and len(model) == 1
                and model.exists()
                and model.provider_id == self
                and model.active
                and model.model_use == JEV_MODEL_USE
            ):
                return model.name
            raise UserError(
                _(
                    "Select an active decision model from this provider or a non-empty model name."
                )
            )
        decision_models = self.model_ids.filtered(
            lambda model: model.active and model.model_use == JEV_MODEL_USE
        )
        defaults = decision_models.filtered("default")
        selected = defaults[:1] or decision_models[:1]
        return selected.name if selected else JEV_DEFAULT_MODEL

    @api.model
    def _jev_extract_predicate_items(self, predicates):
        """Extract ``(key, spec)`` pairs from a dict or list of predicates."""
        if not predicates:
            raise UserError(
                _("At least one decision predicate is required for TypeSafe Jev.")
            )
        if isinstance(predicates, dict):
            return list(predicates.items())
        if isinstance(predicates, (list, tuple)):
            items = []
            for entry in predicates:
                if not isinstance(entry, dict):
                    raise UserError(_("Each predicate in a list must be a dictionary."))
                key = entry.get("name") or entry.get("id") or entry.get("key")
                if not key or not isinstance(key, str):
                    raise UserError(
                        _("Each predicate dictionary must include a string 'name'.")
                    )
                spec = {
                    k: v for k, v in entry.items() if k not in ("name", "id", "key")
                }
                items.append((key, spec))
            return items
        raise UserError(
            _("Predicates must be a non-empty dictionary or list of dictionaries.")
        )

    @api.model
    def _jev_build_question_spec(self, pred_key, spec):
        """Validate and normalize a single Jev ``noul`` question specification."""
        if isinstance(spec, str):
            instructions = spec.strip()
            if not instructions:
                raise UserError(
                    _("Predicate '%(predicate)s' must have non-empty instructions.")
                    % {"predicate": pred_key}
                )
            return {
                "type": "noul",
                "instructions": instructions,
            }
        if isinstance(spec, dict):
            raw_instructions = spec.get("instructions")
            if not isinstance(raw_instructions, str):
                raise UserError(_("Predicate instructions must be a non-empty string."))
            instructions = raw_instructions.strip()
            if not instructions:
                raise UserError(
                    _("Predicate '%(predicate)s' must have non-empty instructions.")
                    % {"predicate": pred_key}
                )
            if spec.get("type", "noul") != "noul":
                raise UserError(
                    _("TypeSafe Jev supports only the 'noul' predicate type.")
                )
            question: dict[str, object] = {
                "type": "noul",
                "instructions": instructions,
            }
            if spec.get("criteria") is not None:
                if not isinstance(spec["criteria"], dict):
                    raise UserError(
                        _(
                            "Criteria for predicate '%(predicate)s' must be a dictionary."
                        )
                        % {"predicate": pred_key}
                    )
                question["criteria"] = dict(spec["criteria"])
            return question
        raise UserError(
            _(
                "Predicate '%(predicate)s' must be a question dictionary or instruction string."
            )
            % {"predicate": pred_key}
        )

    @api.model
    def _jev_normalize_predicates(self, predicates):
        """Normalize predicates into a TypeSafe Jev ``questions`` dictionary."""
        items = self._jev_extract_predicate_items(predicates)
        questions = {}
        for key, spec in items:
            if not isinstance(key, str) or not key.strip():
                raise UserError(_("Predicate keys must be non-empty strings."))
            pred_key = key.strip()
            if pred_key in questions:
                raise UserError(
                    _(
                        "Duplicate predicate key '%(predicate)s' in TypeSafe Jev "
                        "decision request."
                    )
                    % {"predicate": pred_key}
                )
            questions[pred_key] = self._jev_build_question_spec(pred_key, spec)
        return questions

    @api.model
    def _jev_parse_answers(self, response_json, expected_keys=(), status_code=200):
        """Extract per-predicate probabilities from a Jev SystemOne response."""
        if not isinstance(response_json, dict):
            raise UserError(
                _(
                    "TypeSafe Jev API returned an invalid response structure "
                    "(HTTP status %(status)s)."
                )
                % {"status": status_code}
            )

        answers = response_json.get("answers")
        if not isinstance(answers, dict) or not answers:
            raise UserError(
                _(
                    "TypeSafe Jev API response is missing the 'answers' object "
                    "(HTTP status %(status)s)."
                )
                % {"status": status_code}
            )

        if expected_keys and set(answers) - set(expected_keys):
            raise UserError(_("TypeSafe Jev API returned unexpected answer keys."))

        probabilities = {}
        for key, answer in answers.items():
            raw_prob = answer.get("noul") if isinstance(answer, dict) else answer
            if raw_prob is None or isinstance(raw_prob, bool):
                raise UserError(
                    _(
                        "TypeSafe Jev API response is missing a 'noul' score for "
                        "predicate '%(predicate)s'."
                    )
                    % {"predicate": key}
                )
            try:
                prob = float(raw_prob)
            except (TypeError, ValueError):
                raise UserError(
                    _(
                        "TypeSafe Jev API returned a non-numeric probability for "
                        "predicate '%(predicate)s'."
                    )
                    % {"predicate": key}
                ) from None
            if not math.isfinite(prob) or prob < 0.0 or prob > 1.0:
                raise UserError(
                    _(
                        "TypeSafe Jev API returned an out-of-range probability for "
                        "predicate '%(predicate)s' (expected a finite score in [0.0, 1.0])."
                    )
                    % {"predicate": key}
                )
            probabilities[key] = prob

        for expected_key in expected_keys:
            if expected_key not in probabilities:
                raise UserError(
                    _(
                        "TypeSafe Jev API response omitted requested predicate "
                        "'%(predicate)s'."
                    )
                    % {"predicate": expected_key}
                )

        return probabilities

    def jev_models(self, model_id=None):
        """Yield available TypeSafe Jev models (seeded models or ``jev-1.14.0``)."""
        self.ensure_one()
        seeded_names = [
            m.name
            for m in self.model_ids
            if m.active and m.model_use == JEV_MODEL_USE and m.name
        ]
        model_names = seeded_names or [JEV_DEFAULT_MODEL]
        if model_id:
            model_names = [name for name in model_names if name == model_id]

        for name in model_names:
            yield {
                "name": name,
                "details": {
                    "id": name,
                    "display_name": name,
                    "capabilities": [JEV_MODEL_USE],
                },
            }

    def jev_normalize_prepend_messages(self, prepend_messages):
        """Pass prepend messages through so ``chat()`` reaches ``jev_chat()``."""
        return prepend_messages or []

    def jev_chat(
        self,
        messages,
        model=None,
        stream=False,
        tools=None,
        prepend_messages=None,
        **kwargs,
    ):
        """Raise UserError because TypeSafe Jev is a typed decision API, not chat."""
        raise UserError(
            _(
                "TypeSafe Jev is a typed decision API and does not support chat "
                "or streaming. Use jev_decide() instead."
            )
        )

    def jev_embedding(self, texts, model=None):
        """Raise UserError because TypeSafe Jev does not support embeddings."""
        raise UserError(
            _(
                "TypeSafe Jev is a typed decision API and does not support "
                "embeddings. Use jev_decide() instead."
            )
        )

    def jev_generate(self, input_data, model=None, stream=False, **kwargs):
        """Raise UserError because TypeSafe Jev does not support generation."""
        raise UserError(
            _(
                "TypeSafe Jev is a typed decision API and does not support "
                "content generation or streaming. Use jev_decide() instead."
            )
        )

    def jev_format_messages(self, messages, system_prompt=None, model=None):
        """Raise UserError because TypeSafe Jev does not format chat messages."""
        raise UserError(
            _(
                "TypeSafe Jev is a typed decision API and does not support chat "
                "message formatting. Use jev_decide() instead."
            )
        )

    def jev_format_tools(self, tools):
        """Raise UserError because TypeSafe Jev does not support tool calling."""
        raise UserError(
            _(
                "TypeSafe Jev is a typed decision API and does not support tool "
                "calling. Use jev_decide() instead."
            )
        )
