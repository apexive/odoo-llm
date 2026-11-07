# Copyright 2026 Lijo Antony
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html).

from types import SimpleNamespace
from unittest.mock import Mock, patch

from odoo.tests.common import TransactionCase, tagged


class ModelPages:
    """Expose the first page through data and all pages through iteration."""

    def __init__(self, pages):
        self.pages = pages
        self.data = pages[0]

    def __iter__(self):
        for page in self.pages:
            yield from page


@tagged("post_install", "-at_install")
class TestAnthropicModelPagination(TransactionCase):
    def setUp(self):
        super().setUp()
        self.provider = self.env["llm.provider"].create(
            {"name": "Model pagination test", "service": "anthropic"}
        )

    def test_catalog_includes_second_page(self):
        client = Mock()
        client.models.list.return_value = ModelPages(
            [
                [SimpleNamespace(id="claude-3-first")],
                [SimpleNamespace(id="claude-3-second")],
            ]
        )
        with patch.object(
            type(self.provider), "anthropic_get_client", return_value=client
        ):
            models = list(self.provider.list_models())
        self.assertEqual(
            [model["name"] for model in models], ["claude-3-first", "claude-3-second"]
        )
        client.models.list.assert_called_once_with()

    def test_empty_catalog(self):
        client = Mock()
        client.models.list.return_value = ModelPages([[]])
        with patch.object(
            type(self.provider), "anthropic_get_client", return_value=client
        ):
            self.assertEqual(list(self.provider.list_models()), [])

    def test_specific_model_uses_retrieve(self):
        client = Mock()
        client.models.retrieve.return_value = SimpleNamespace(id="claude-3-specific")
        with patch.object(
            type(self.provider), "anthropic_get_client", return_value=client
        ):
            models = list(self.provider.list_models(model_id="claude-3-specific"))
        self.assertEqual([model["name"] for model in models], ["claude-3-specific"])
        client.models.retrieve.assert_called_once_with("claude-3-specific")
        client.models.list.assert_not_called()
