# Copyright 2026 Lijo Antony
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html).

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAnthropicSystemMessages(TransactionCase):
    def test_system_messages_reach_sdk_in_order(self):
        provider = self.env["llm.provider"].create(
            {"name": "System message test", "service": "anthropic"}
        )
        model = self.env["llm.model"].create(
            {"name": "claude-3-sonnet", "provider_id": provider.id, "model_use": "chat"}
        )
        prepend = [
            {"role": "system", "content": "First instruction"},
            {"role": "user", "content": "First question"},
            {
                "role": "system",
                "content": [{"type": "text", "text": "Second instruction"}],
            },
            {"role": "system", "content": ""},
            {"role": "assistant", "content": "Earlier answer"},
            {"role": "user", "content": "Next question"},
        ]
        original = deepcopy(prepend)
        for stream in (False, True):
            with self.subTest(stream=stream):
                create = Mock(return_value=SimpleNamespace(content=[]))
                client = MagicMock()
                client.messages.create = create
                client.messages.stream.return_value.__enter__.return_value = []
                with patch.object(
                    type(provider), "anthropic_get_client", return_value=client
                ):
                    result = model.chat(
                        self.env["mail.message"],
                        prepend_messages=prepend,
                        stream=stream,
                    )
                    if stream:
                        list(result)
                request = client.messages.stream if stream else create
                request.assert_called_once()
                params = request.call_args.kwargs
                self.assertEqual(
                    params["system"], "First instruction\n\nSecond instruction"
                )
                self.assertEqual(
                    params["messages"], [m for m in prepend if m["role"] != "system"]
                )
                self.assertEqual(prepend, original)

    def test_empty_system_messages_are_omitted(self):
        provider = self.env["llm.provider"].create(
            {"name": "Empty system test", "service": "anthropic"}
        )
        model = self.env["llm.model"].create(
            {"name": "claude-3-sonnet", "provider_id": provider.id, "model_use": "chat"}
        )
        client = MagicMock()
        client.messages.create.return_value = SimpleNamespace(content=[])
        with patch.object(type(provider), "anthropic_get_client", return_value=client):
            model.chat(
                self.env["mail.message"],
                prepend_messages=[{"role": "system", "content": ""}],
            )
        self.assertNotIn("system", client.messages.create.call_args.kwargs)
