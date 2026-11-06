# Copyright 2026 Lijo Antony
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html).

from unittest.mock import MagicMock, patch

import requests

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

from ..models.jev_provider import (
    JEV_DEFAULT_API_BASE,
    JEV_DEFAULT_MODEL,
    JEV_DEFAULT_TIMEOUT,
    JEV_MODEL_USE,
    JEV_SERVICE,
    JEV_SERVICE_LABEL,
)


@tagged("post_install", "-at_install")
class TestJevProvider(TransactionCase):
    """Tests for the TypeSafe Jev LLM provider (``llm_jev``)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.publisher = cls.env.ref("llm_jev.llm_publisher_typesafe")
        cls.seeded_provider = cls.env.ref("llm_jev.llm_provider_jev")
        cls.seeded_model = cls.env.ref("llm_jev.llm_model_jev_1_14_0")
        cls.secret_api_key = "ARTIFICIAL_TEST_KEY_DO_NOT_USE"
        cls.provider = cls.env["llm.provider"].create(
            {
                "name": "TypeSafe Jev Test Provider",
                "service": JEV_SERVICE,
                "api_key": cls.secret_api_key,
                "api_base": JEV_DEFAULT_API_BASE,
            }
        )
        cls.model = cls.env["llm.model"].create(
            {
                "name": JEV_DEFAULT_MODEL,
                "provider_id": cls.provider.id,
                "publisher_id": cls.publisher.id,
                "model_use": JEV_MODEL_USE,
                "default": True,
            }
        )

    def _sample_state_and_predicates(self):
        state = {"sample": "ARTIFICIAL_PRIVATE_MARKER", "values": [1, 2, 3]}
        predicates = {
            "positive": {
                "instructions": "Are all values positive?",
                "criteria": {"true": "All positive", "false": "Otherwise"},
            },
            "sorted": {
                "instructions": "Are values sorted?",
                "criteria": {"true": "Sorted", "false": "Otherwise"},
            },
            "empty": {
                "instructions": "Is the list empty?",
                "criteria": {"true": "Empty", "false": "Otherwise"},
            },
        }
        return state, predicates

    def test_service_registered_and_seeded_records(self):
        """Service ('jev', 'TypeSafe Jev') and seeded publisher/model records exist."""
        services = self.env["llm.provider"]._get_available_services()
        self.assertIn((JEV_SERVICE, JEV_SERVICE_LABEL), services)

        selection = self.env["llm.provider"]._selection_service()
        self.assertIn((JEV_SERVICE, JEV_SERVICE_LABEL), selection)

        model_usages = self.env["llm.model"]._get_available_model_usages()
        self.assertIn((JEV_MODEL_USE, "Decision"), model_usages)

        self.assertEqual(self.publisher.name, "TypeSafe")
        self.assertTrue(self.publisher.official)
        self.assertTrue(self.publisher.frontier)

        self.assertEqual(self.seeded_provider.service, JEV_SERVICE)
        self.assertEqual(self.seeded_model.name, JEV_DEFAULT_MODEL)
        self.assertEqual(self.seeded_model.model_use, JEV_MODEL_USE)
        self.assertEqual(self.seeded_model.provider_id, self.seeded_provider)
        self.assertEqual(self.seeded_model.publisher_id, self.publisher)
        self.assertTrue(self.seeded_model.default)

        self.assertEqual(
            self.provider._determine_model_use(JEV_DEFAULT_MODEL, [JEV_MODEL_USE]),
            JEV_MODEL_USE,
        )

        models_list = list(self.provider.list_models())
        self.assertEqual(len(models_list), 1)
        self.assertEqual(models_list[0]["name"], JEV_DEFAULT_MODEL)
        self.assertIn("decision", models_list[0]["details"]["capabilities"])

        filtered = list(self.provider.list_models(model_id=JEV_DEFAULT_MODEL))
        self.assertEqual(len(filtered), 1)
        self.assertEqual(
            list(self.provider.list_models(model_id="non-existent-model")), []
        )

    def test_request_construction_and_response_parsing(self):
        """jev_decide builds the exact /v1/systemone request and parses probabilities."""
        state, predicates = self._sample_state_and_predicates()
        self.assertEqual(
            list(predicates.keys()),
            ["positive", "sorted", "empty"],
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "model": JEV_DEFAULT_MODEL,
            "answers": {
                "positive": {"type": "noul", "noul": 0.08},
                "sorted": {"type": "noul", "noul": 0.96},
                "empty": {"type": "noul", "noul": 0.07},
            },
            "usage": {"input_tokens": 1401, "output_tokens": 67},
        }

        with patch(
            "odoo.addons.llm_jev.models.jev_provider.requests.post",
            return_value=mock_response,
        ) as mock_post:
            probabilities = self.provider.jev_decide(state, predicates)

        self.assertEqual(
            probabilities,
            {
                "positive": 0.08,
                "sorted": 0.96,
                "empty": 0.07,
            },
        )

        mock_post.assert_called_once()
        call_args, call_kwargs = mock_post.call_args
        self.assertEqual(call_args[0], "https://api.typesafe.ai/v1/systemone")
        self.assertEqual(call_kwargs["timeout"], JEV_DEFAULT_TIMEOUT)
        self.assertEqual(
            call_kwargs["headers"],
            {
                "Authorization": f"Bearer {self.secret_api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

        sent_payload = call_kwargs["json"]
        self.assertEqual(sent_payload["model"], JEV_DEFAULT_MODEL)
        self.assertEqual(sent_payload["state"], state)
        sent_questions = sent_payload["questions"]
        self.assertEqual(
            set(sent_questions.keys()),
            {"positive", "sorted", "empty"},
        )
        for q_key in ("positive", "sorted", "empty"):
            self.assertEqual(sent_questions[q_key]["type"], "noul")
            self.assertTrue(sent_questions[q_key]["instructions"])
            self.assertIn("true", sent_questions[q_key]["criteria"])
            self.assertIn("false", sent_questions[q_key]["criteria"])

    def test_decide_dispatch_and_list_predicates(self):
        """provider.decide() dispatches to jev_decide() and supports list predicates."""
        state, _ = self._sample_state_and_predicates()
        list_predicates = [
            {
                "name": "positive",
                "instructions": "Are all values positive?",
                "criteria": {"true": "All positive", "false": "Other"},
            },
            {
                "name": "empty",
                "instructions": "Is the list empty?",
            },
        ]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "model": JEV_DEFAULT_MODEL,
            "answers": {
                "positive": {"type": "noul", "noul": 0.91},
                "empty": {"type": "noul", "noul": 0.04},
            },
        }

        with patch(
            "odoo.addons.llm_jev.models.jev_provider.requests.post",
            return_value=mock_response,
        ) as mock_post:
            result = self.provider.decide(
                state, list_predicates, model=self.model, timeout=3.5
            )

        self.assertEqual(result, {"positive": 0.91, "empty": 0.04})
        self.assertEqual(mock_post.call_args.kwargs["timeout"], 3.5)
        self.assertEqual(
            mock_post.call_args.kwargs["json"]["questions"]["empty"]["type"],
            "noul",
        )

    def test_missing_api_key_raises_user_error(self):
        """Missing or blank API key raises UserError without making HTTP calls."""
        state, predicates = self._sample_state_and_predicates()

        keyless_provider = self.env["llm.provider"].create(
            {
                "name": "TypeSafe Jev Keyless Provider",
                "service": JEV_SERVICE,
                "api_key": False,
            }
        )
        blank_key_provider = self.env["llm.provider"].create(
            {
                "name": "TypeSafe Jev Blank Key Provider",
                "service": JEV_SERVICE,
                "api_key": "   ",
            }
        )

        with patch(
            "odoo.addons.llm_jev.models.jev_provider.requests.post"
        ) as mock_post:
            with self.assertRaises(UserError):
                keyless_provider.jev_get_client()
            with self.assertRaises(UserError):
                _ = keyless_provider.client
            with self.assertRaises(UserError):
                keyless_provider.jev_decide(state, predicates)
            with self.assertRaises(UserError):
                blank_key_provider.jev_decide(state, predicates)
            mock_post.assert_not_called()

        client = self.provider.jev_get_client()
        self.assertNotIn(self.secret_api_key, repr(client))
        self.assertNotIn(self.secret_api_key, str(client))

    def test_http_error_and_timeout_raise_user_error_without_leaking_key_or_payload(
        self,
    ):
        """HTTP errors and timeouts raise UserError with status, never key or payload."""
        state, predicates = self._sample_state_and_predicates()
        sensitive_marker = "ARTIFICIAL_PRIVATE_MARKER"

        # 1. Non-200 HTTP response (e.g. 503 Service Unavailable)
        error_response = MagicMock()
        error_response.status_code = 503
        error_response.text = (
            f"upstream failure with {self.secret_api_key} and {sensitive_marker}"
        )
        with patch(
            "odoo.addons.llm_jev.models.jev_provider.requests.post",
            return_value=error_response,
        ):
            with self.assertRaises(UserError) as ctx:
                self.provider.jev_decide(state, predicates)
        err_msg = str(ctx.exception)
        self.assertIn("503", err_msg)
        self.assertNotIn(self.secret_api_key, err_msg)
        self.assertNotIn(sensitive_marker, err_msg)

        # 2. requests.exceptions.HTTPError with response status 401
        resp_401 = MagicMock()
        resp_401.status_code = 401
        http_exc = requests.exceptions.HTTPError(
            f"401 Unauthorized for {self.secret_api_key} payload {sensitive_marker}",
            response=resp_401,
        )
        with patch(
            "odoo.addons.llm_jev.models.jev_provider.requests.post",
            side_effect=http_exc,
        ):
            with self.assertRaises(UserError) as ctx_401:
                self.provider.jev_decide(state, predicates)
        err_401 = str(ctx_401.exception)
        self.assertIn("401", err_401)
        self.assertNotIn(self.secret_api_key, err_401)
        self.assertNotIn(sensitive_marker, err_401)

        # 3. requests.exceptions.Timeout / ReadTimeout
        timeout_exc = requests.exceptions.ReadTimeout(
            f"Read timed out (key={self.secret_api_key}, body={sensitive_marker})"
        )
        with patch(
            "odoo.addons.llm_jev.models.jev_provider.requests.post",
            side_effect=timeout_exc,
        ):
            with self.assertRaises(UserError) as ctx_timeout:
                self.provider.jev_decide(state, predicates)
        err_timeout = str(ctx_timeout.exception)
        self.assertIn("timeout", err_timeout.lower())
        self.assertNotIn(self.secret_api_key, err_timeout)
        self.assertNotIn(sensitive_marker, err_timeout)

        # 4. Generic ConnectionError
        conn_exc = requests.exceptions.ConnectionError(
            f"Connection reset (key={self.secret_api_key}, body={sensitive_marker})"
        )
        with patch(
            "odoo.addons.llm_jev.models.jev_provider.requests.post",
            side_effect=conn_exc,
        ):
            with self.assertRaises(UserError) as ctx_conn:
                self.provider.jev_decide(state, predicates)
        err_conn = str(ctx_conn.exception)
        self.assertIn("connection_error", err_conn)
        self.assertNotIn(self.secret_api_key, err_conn)
        self.assertNotIn(sensitive_marker, err_conn)

    def test_invalid_inputs_and_malformed_response_raise_user_error(self):
        """Empty state/predicates, duplicate keys, or invalid scores raise UserError."""
        state, predicates = self._sample_state_and_predicates()

        with self.assertRaises(UserError):
            self.provider.jev_decide({}, predicates)
        with self.assertRaises(UserError):
            self.provider.jev_decide(state, {})

        # Duplicate normalized predicate names in dict (via whitespace) and list
        with self.assertRaises(UserError) as ctx_dup_dict:
            self.provider.jev_decide(
                state,
                {
                    "route": "First question",
                    " route ": "Second question colliding after strip",
                },
            )
        self.assertIn("route", str(ctx_dup_dict.exception))

        with self.assertRaises(UserError) as ctx_dup_list:
            self.provider.jev_decide(
                state,
                [
                    {"name": "positive", "instructions": "First"},
                    {"name": " positive ", "instructions": "Duplicate"},
                ],
            )
        self.assertIn("positive", str(ctx_dup_list.exception))

        bad_json_resp = MagicMock()
        bad_json_resp.status_code = 200
        bad_json_resp.json.side_effect = ValueError("No JSON")
        with patch(
            "odoo.addons.llm_jev.models.jev_provider.requests.post",
            return_value=bad_json_resp,
        ):
            with self.assertRaises(UserError) as ctx_json:
                self.provider.jev_decide(state, predicates)
        self.assertIn("200", str(ctx_json.exception))

        incomplete_resp = MagicMock()
        incomplete_resp.status_code = 200
        incomplete_resp.json.return_value = {
            "model": JEV_DEFAULT_MODEL,
            "answers": {
                "positive": {"type": "noul", "noul": 0.10},
            },
        }
        with patch(
            "odoo.addons.llm_jev.models.jev_provider.requests.post",
            return_value=incomplete_resp,
        ):
            with self.assertRaises(UserError) as ctx_missing:
                self.provider.jev_decide(state, predicates)
        self.assertIn("sorted", str(ctx_missing.exception))

        # Non-finite and out-of-range scores must raise UserError
        for invalid_score in (float("nan"), float("inf"), float("-inf"), -0.01, 1.01):
            bad_score_resp = MagicMock()
            bad_score_resp.status_code = 200
            bad_score_resp.json.return_value = {
                "model": JEV_DEFAULT_MODEL,
                "answers": {
                    "positive": {"type": "noul", "noul": invalid_score},
                    "sorted": {"type": "noul", "noul": 0.50},
                    "empty": {"type": "noul", "noul": 0.10},
                },
            }
            with patch(
                "odoo.addons.llm_jev.models.jev_provider.requests.post",
                return_value=bad_score_resp,
            ):
                with self.assertRaises(UserError) as ctx_range:
                    self.provider.jev_decide(state, predicates)
            self.assertIn("positive", str(ctx_range.exception))

    def test_unsupported_chat_and_framework_methods_raise_user_error(self):
        """Unsupported chat, streaming, embedding, and generation raise UserError."""
        empty_messages = self.env["mail.message"].browse()

        with self.assertRaises(UserError) as ctx_chat:
            self.provider.chat(empty_messages)
        self.assertIn("jev_decide", str(ctx_chat.exception))

        with self.assertRaises(UserError):
            self.provider.chat(empty_messages, stream=True)

        with self.assertRaises(UserError):
            self.provider.embedding(["sample text"])

        with self.assertRaises(UserError):
            self.provider.generate("sample input")

        with self.assertRaises(UserError):
            self.provider.generate("sample input", stream=True)

        with self.assertRaises(UserError):
            self.provider.format_messages(empty_messages)

        with self.assertRaises(UserError):
            self.provider.format_tools([])

        with self.assertRaises(UserError):
            self.model.chat(empty_messages)

        with self.assertRaises(UserError):
            self.model.embedding(["sample text"])

    def test_invalid_timeout_rejected_before_http(self):
        state, predicates = self._sample_state_and_predicates()
        for timeout in (
            0,
            -1,
            float("inf"),
            float("-inf"),
            float("nan"),
            "invalid",
            "3.5",
            True,
            [],
            {},
        ):
            with (
                self.subTest(timeout=timeout),
                patch("odoo.addons.llm_jev.models.jev_provider.requests.post") as post,
            ):
                with self.assertRaisesRegex(UserError, "timeout"):
                    self.provider.decide(state, predicates, timeout=timeout)
                post.assert_not_called()

    def test_invalid_instructions_and_types_rejected_before_http(self):
        for spec in (
            {"instructions": 12},
            {"instructions": ["text"]},
            {"instructions": True},
            {"instructions": {}},
            {"instructions": " "},
            {"instructions": "Test", "type": "boolean"},
            {"instructions": "Test", "type": False},
            {"instructions": "Test", "criteria": []},
            7,
        ):
            with (
                self.subTest(spec=spec),
                patch("odoo.addons.llm_jev.models.jev_provider.requests.post") as post,
            ):
                with self.assertRaises(UserError):
                    self.provider.decide({"sample": 1}, {"check": spec})
                post.assert_not_called()

    def test_unexpected_answer_keys_rejected(self):
        with self.assertRaisesRegex(UserError, "unexpected"):
            self.provider._jev_parse_answers(
                {"answers": {"check": 0.5, "extra": 0.2}}, expected_keys=("check",)
            )

    def test_foreign_archived_and_invalid_models_rejected(self):
        foreign = self.env["llm.model"].create(
            {
                "name": "artificial-foreign",
                "provider_id": self.seeded_provider.id,
                "model_use": JEV_MODEL_USE,
            }
        )
        state, predicates = self._sample_state_and_predicates()
        self.model.active = False
        for model in (foreign, self.model.with_context(active_test=False), 42, " "):
            with (
                self.subTest(model=model),
                patch("odoo.addons.llm_jev.models.jev_provider.requests.post") as post,
            ):
                with self.assertRaises(UserError):
                    self.provider.decide(state, predicates, model=model)
                post.assert_not_called()
        self.assertEqual(self.provider._jev_resolve_model_name(), JEV_DEFAULT_MODEL)
        self.assertEqual(
            list(self.provider.list_models()),
            [
                {
                    "name": JEV_DEFAULT_MODEL,
                    "details": {
                        "id": JEV_DEFAULT_MODEL,
                        "display_name": JEV_DEFAULT_MODEL,
                        "capabilities": [JEV_MODEL_USE],
                    },
                }
            ],
        )

    def test_url_normalization(self):
        from ..models.jev_provider import JevClient

        for base in (
            "https://api.typesafe.ai",
            "https://api.typesafe.ai/",
            "https://api.typesafe.ai/v1",
            "https://api.typesafe.ai/v1/",
            "https://api.typesafe.ai/v1/systemone",
            "https://api.typesafe.ai/v1/systemone/",
        ):
            with self.subTest(base=base):
                self.assertEqual(
                    JevClient("ARTIFICIAL_TEST_KEY_DO_NOT_USE", api_base=base).endpoint,
                    "https://api.typesafe.ai/v1/systemone",
                )

    def test_answer_validation_and_boundaries(self):
        for value in (
            True,
            False,
            None,
            "invalid",
            {},
            [],
            float("nan"),
            float("inf"),
            -0.1,
            1.1,
        ):
            with self.subTest(value=value), self.assertRaises(UserError):
                self.provider._jev_parse_answers(
                    {"answers": {"check": {"noul": value}}}, expected_keys=("check",)
                )
        for response in (
            [],
            {},
            {"answers": []},
            {"answers": {}},
            {"answers": {"other": 0.5}},
        ):
            with self.subTest(response=response), self.assertRaises(UserError):
                self.provider._jev_parse_answers(response, expected_keys=("check",))
        for value in (0, 1, "0.5"):
            self.assertEqual(
                self.provider._jev_parse_answers(
                    {"answers": {"check": value}}, expected_keys=("check",)
                ),
                {"check": float(value)},
            )

    def test_company_defaults_and_stock_access(self):
        self.assertEqual(self.seeded_provider.company_id, self.env.company)
        company = self.env["res.company"].create({"name": "Artificial Second Company"})
        provider = (
            self.env["llm.provider"]
            .with_company(company)
            .create({"name": "Artificial Company Provider", "service": JEV_SERVICE})
        )
        self.assertEqual(provider.company_id, company)
        user = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Artificial Internal User",
                    "login": "artificial_jev_user",
                    "company_id": self.env.company.id,
                    "company_ids": [(6, 0, [self.env.company.id])],
                    "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
                }
            )
        )
        # The stock provider rule permits internal users to read every company.
        self.assertEqual(
            provider.with_context(allowed_company_ids=user.company_ids.ids)
            .with_user(user)
            .name,
            "Artificial Company Provider",
        )
        from odoo.exceptions import AccessError

        with self.assertRaises(AccessError):
            provider.with_context(allowed_company_ids=user.company_ids.ids).with_user(
                user
            ).write({"name": "Forbidden change"})
