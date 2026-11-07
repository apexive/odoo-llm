# Copyright 2026 Lijo Antony
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html).

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestPromptTestAccess(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(
            cls.env,
            login="prompt_access_user",
            groups="base.group_user,base.group_erp_manager",
        )
        cls.allowed = cls.env["res.partner"].create(
            {"name": "Visible fixture", "comment": "ARTIFICIAL_VISIBLE_MARKER"}
        )
        cls.denied = cls.env["res.partner"].create(
            {"name": "Restricted fixture", "comment": "ARTIFICIAL_PRIVATE_MARKER"}
        )
        cls.env["ir.rule"].create(
            {
                "name": "Restricted fixture access",
                "model_id": cls.env["ir.model"]._get_id("res.partner"),
                "domain_force": repr([("id", "!=", cls.denied.id)]),
            }
        )
        cls.env.invalidate_all()
        cls.prompt = cls.env["llm.prompt"].create(
            {
                "name": "Record access fixture",
                "template": "{{ related_record.get_field('comment', 'Unavailable') }}",
                "format": "text",
            }
        )

    def _wizard(self, partner):
        return (
            self.env["llm.prompt.test"]
            .with_user(self.user)
            .create(
                {
                    "prompt_id": self.prompt.id,
                    "related_record_ref": f"res.partner,{partner.id}",
                    "test_context": "{}",
                }
            )
        )

    @mute_logger("odoo.addons.llm_thread.models.llm_thread")
    def test_restricted_record_is_not_rendered(self):
        with self.assertRaises(AccessError):
            self.denied.with_user(self.user).read(["comment"])
        wizard = self._wizard(self.denied)
        wizard.action_evaluate_prompt()
        for field in (
            "rendered_template",
            "messages_json",
            "messages_yaml",
            "messages_text",
        ):
            self.assertNotIn("ARTIFICIAL_PRIVATE_MARKER", wizard[field] or "")

    def test_authorized_record_is_rendered(self):
        wizard = self._wizard(self.allowed)
        wizard.action_evaluate_prompt()
        self.assertFalse(wizard.has_error, wizard.error_message)
        self.assertIn("ARTIFICIAL_VISIBLE_MARKER", wizard.rendered_template)

    def test_mock_thread_retains_the_caller(self):
        mock = self._wizard(self.allowed)._create_mock_thread()
        self.assertEqual(mock.env.uid, self.user.id)
        self.assertFalse(mock.env.su)
