# Copyright 2026 Lijo Antony
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html).

import json
from unittest.mock import patch

from odoo.tests.common import HttpCase, new_test_user, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestThreadClientUpdate(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(
            cls.env,
            login="thread_update_user",
            password="test",
            groups="base.group_user",
        )
        cls.other_user = new_test_user(
            cls.env, login="other_thread_user", groups="base.group_user"
        )
        providers = cls.env["llm.provider"]
        with patch.object(
            type(providers), "_get_available_services", return_value=[("test", "Test")]
        ):
            cls.provider = providers.create(
                {"name": "Update fixture", "service": "test"}
            )
        cls.model = cls.env["llm.model"].create(
            {"name": "Update fixture model", "provider_id": cls.provider.id}
        )
        cls.thread = cls.env["llm.thread"].create(
            {
                "name": "Original title",
                "user_id": cls.user.id,
                "provider_id": cls.provider.id,
                "model_id": cls.model.id,
            }
        )
        cls.foreign_thread = cls.thread.copy(
            {"name": "Other user's thread", "user_id": cls.other_user.id}
        )

    def _update(self, thread_id, **values):
        response = self.url_open(
            f"/llm/thread/{thread_id}/update",
            data=json.dumps(
                {"jsonrpc": "2.0", "method": "call", "id": 1, "params": values}
            ),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertNotIn("error", payload, payload)
        return payload["result"]

    def setUp(self):
        super().setUp()
        self.authenticate(self.user.login, "test")

    def test_rename(self):
        self.assertEqual(
            self._update(self.thread.id, name="New title"), {"status": "success"}
        )
        self.thread.invalidate_recordset()
        self.assertEqual(self.thread.name, "New title")

    def test_ignore_non_title_fields(self):
        fields = {
            "active": False,
            "model": "res.users",
            "res_id": self.other_user.id,
            "provider_id": False,
            "model_id": False,
            "user_id": self.other_user.id,
            "tool_ids": [(6, 0, self.env["llm.tool"].search([], limit=1).ids)],
        }
        for field, value in fields.items():
            with self.subTest(field=field):
                thread = self.thread.copy()
                before = thread.read([field])[0][field]
                result = self._update(thread.id, **{field: value})
                self.assertEqual(result, {"status": "success"})
                thread.invalidate_recordset()
                self.assertEqual(thread.read([field])[0][field], before)

    def test_mixed_fields_rename_only(self):
        result = self._update(
            self.thread.id, name="Safe title", model="res.users", res_id=self.user.id
        )
        self.assertEqual(result, {"status": "success"})
        self.thread.invalidate_recordset()
        self.assertEqual(self.thread.name, "Safe title")
        self.assertFalse(self.thread.model)
        self.assertFalse(self.thread.res_id)

    @mute_logger("odoo.addons.llm_thread.controllers.main")
    def test_foreign_thread_returns_neutral_error(self):
        result = self._update(self.foreign_thread.id, name="Rejected title")
        self.assertEqual(
            result, {"status": "error", "error": "Could not update the thread."}
        )
        self.foreign_thread.invalidate_recordset()
        self.assertEqual(self.foreign_thread.name, "Other user's thread")

    @mute_logger("odoo.addons.llm_thread.controllers.main")
    def test_missing_thread_returns_neutral_error(self):
        missing_id = max(self.env["llm.thread"].search([]).ids) + 1000
        result = self._update(missing_id, name="Rejected title")
        self.assertEqual(
            result, {"status": "error", "error": "Could not update the thread."}
        )

    def test_empty_update(self):
        self.assertEqual(self._update(self.thread.id), {"status": "success"})

    def test_unknown_field_is_ignored(self):
        self.assertEqual(
            self._update(self.thread.id, unknown_field="ignored"), {"status": "success"}
        )
