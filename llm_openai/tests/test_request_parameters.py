# Copyright 2026 Lijo Antony
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html).

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestOpenAIRequestParameters(TransactionCase):
    def setUp(self):
        super().setUp()
        self.provider = self.env["llm.provider"].create(
            {"name": "Completion parameter test", "service": "openai"}
        )
        self.model = self.env["llm.model"].create(
            {"name": "gpt-4o", "provider_id": self.provider.id, "model_use": "chat"}
        )

    def _request(self, stream=False, **kwargs):
        client = MagicMock()
        message = SimpleNamespace(content="Answer", tool_calls=None)
        client.chat.completions.create.return_value = (
            []
            if stream
            else SimpleNamespace(choices=[SimpleNamespace(message=message)])
        )
        with patch.object(
            type(self.provider), "openai_get_client", return_value=client
        ):
            response = self.model.chat(
                self.env["mail.message"], stream=stream, **kwargs
            )
            if stream:
                list(response)
        client.chat.completions.create.assert_called_once()
        params = client.chat.completions.create.call_args.kwargs
        self.assertEqual(params["stream"], stream)
        return params

    def test_forward_parameters_in_both_modes(self):
        options = {
            "max_tokens": 64,
            "temperature": 0.2,
            "top_p": 0.9,
            "frequency_penalty": 0.1,
            "presence_penalty": 0.2,
            "stop": ["END"],
            "seed": 42,
            "response_format": {"type": "json_object"},
            "timeout": 7,
        }
        for stream in (False, True):
            with self.subTest(stream=stream):
                params = self._request(stream=stream, **options)
                for key, value in options.items():
                    self.assertEqual(params.get(key), value)

    def test_zero_values_are_preserved(self):
        keys = (
            "max_tokens",
            "temperature",
            "top_p",
            "frequency_penalty",
            "presence_penalty",
            "seed",
            "timeout",
        )
        for stream in (False, True):
            params = self._request(stream=stream, **dict.fromkeys(keys, 0))
            for key in keys:
                self.assertEqual(params.get(key), 0)

    def test_unset_none_and_unknown_parameters_are_omitted(self):
        keys = (
            "max_tokens",
            "temperature",
            "top_p",
            "frequency_penalty",
            "presence_penalty",
            "stop",
            "seed",
            "response_format",
            "timeout",
            "unknown_option",
        )
        for options in ({}, dict.fromkeys(keys)):
            params = self._request(**options)
            for key in keys:
                self.assertNotIn(key, params)
        self.assertNotIn("unknown_option", self._request(unknown_option="unused"))
