# Copyright 2026 Lijo Antony
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html).

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAnthropicRequestParameters(TransactionCase):
    def setUp(self):
        super().setUp()
        self.provider = self.env["llm.provider"].create(
            {"name": "Request parameter test", "service": "anthropic"}
        )
        self.model = self.env["llm.model"].create(
            {
                "name": "claude-3-sonnet",
                "provider_id": self.provider.id,
                "model_use": "chat",
            }
        )

    def _request(self, stream=False, **kwargs):
        client = MagicMock()
        client.messages.create.return_value = SimpleNamespace(content=[])
        client.messages.stream.return_value.__enter__.return_value = []
        with patch.object(
            type(self.provider), "anthropic_get_client", return_value=client
        ):
            response = self.model.chat(
                self.env["mail.message"], stream=stream, **kwargs
            )
            if stream:
                list(response)
        call = client.messages.stream if stream else client.messages.create
        call.assert_called_once()
        return call.call_args.kwargs

    def test_forward_parameters_in_both_modes(self):
        options = {
            "timeout": 7,
            "temperature": 0.2,
            "top_p": 0.9,
            "stop_sequences": ["END"],
        }
        for stream in (False, True):
            with self.subTest(stream=stream):
                params = self._request(stream=stream, **options)
                for key, value in options.items():
                    self.assertEqual(params.get(key), value)

    def test_zero_values_are_preserved(self):
        for stream in (False, True):
            params = self._request(
                stream=stream, temperature=0, top_p=0, timeout=0, stop_sequences=[]
            )
            for key in ("temperature", "top_p", "timeout"):
                self.assertEqual(params.get(key), 0)
            self.assertEqual(params.get("stop_sequences"), [])

    def test_unset_none_and_unknown_parameters_are_omitted(self):
        keys = ("timeout", "temperature", "top_p", "stop_sequences", "unknown_option")
        for options in ({}, dict.fromkeys(keys)):
            params = self._request(**options)
            for key in keys:
                self.assertNotIn(key, params)
        self.assertNotIn("unknown_option", self._request(unknown_option="unused"))

    def test_thinking_configuration_stays_independent(self):
        params = self._request(
            extended_thinking=True,
            thinking_budget=1024,
            max_tokens=2048,
            temperature=1,
            timeout=7,
        )
        self.assertEqual(params["thinking"], {"type": "enabled", "budget_tokens": 1024})
        self.assertEqual(params["max_tokens"], 2048)
        self.assertEqual(params.get("temperature"), 1)
        self.assertEqual(params.get("timeout"), 7)
        self.assertNotIn("top_p", params)
