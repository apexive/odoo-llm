# Copyright 2026 Lijo Antony
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html).

import os
from unittest.mock import patch

from openai import OpenAI

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMistralClientHost(TransactionCase):
    def test_compatible_client_hosts(self):
        """Select the host before constructing a credential-bearing client."""
        cases = [
            ("mistral", False, "https://api.mistral.ai/v1/"),
            ("mistral", "https://example.test/v1", "https://example.test/v1/"),
            ("openai", False, "https://api.openai.com/v1/"),
            ("openai", "https://example.test/custom", "https://example.test/custom/"),
        ]
        with patch.dict(os.environ):
            os.environ.pop("OPENAI_BASE_URL", None)
            for index, (service, api_base, expected) in enumerate(cases):
                with self.subTest(service=service, api_base=api_base):
                    provider = self.env["llm.provider"].create(
                        {
                            "name": f"Client host fixture {index}",
                            "service": service,
                            "api_key": "ARTIFICIAL_TEST_KEY_DO_NOT_USE",
                            "api_base": api_base,
                        }
                    )
                    with provider.client as client:
                        self.assertIsInstance(client, OpenAI)
                        self.assertEqual(str(client.base_url), expected)
