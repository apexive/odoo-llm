"""Enforcement of requires_user_consent in the tool execution path.

Issue #86; implements requirement 3 of #22 ("modify the processing pipeline to
check for user consent before executing tool calls").
"""

from unittest.mock import patch

from odoo.tests import common, tagged


class ConsentCase(common.TransactionCase):
    """Shared fixture: a real llm.thread carrying real llm.tool records.

    The base llm module registers no provider services (the concrete ones live
    in llm_openai, llm_ollama and friends), so a provider is created behind a
    patched _get_available_services. Nothing here calls a provider -- the
    thread only has to exist so that tool messages have an owner with tool_ids.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Message = cls.env["mail.message"]

        def patched_services():
            return [("test_consent_service", "Test Consent Service")]

        with patch.object(
            type(cls.env["llm.provider"]),
            "_get_available_services",
            patched_services,
        ):
            cls.provider = cls.env["llm.provider"].create(
                {"name": "Consent Test Provider", "service": "test_consent_service"}
            )

        cls.model = cls.env["llm.model"].create(
            {
                "name": "consent-test-model",
                "provider_id": cls.provider.id,
                "model_use": "chat",
            }
        )

    def _make_tool(self, name, requires_consent=True):
        # decorator_method must be unique per tool: llm.tool carries a
        # UNIQUE(decorator_model, decorator_method) constraint, and a single
        # test may need several tools at once.
        return self.env["llm.tool"].create(
            {
                "name": name,
                "description": f"Test tool {name}",
                "implementation": "function",
                "decorator_model": "res.partner",
                "decorator_method": name,
                "requires_user_consent": requires_consent,
            }
        )

    def _patched_execute(self):
        """Stub llm.tool.execute().

        The unit under test is the consent gate, not any particular Odoo
        method. Binding to a real method would make these tests depend on
        whether its annotations happen to resolve -- res.partner.read, for
        instance, is annotated with a name get_type_hints() cannot resolve.
        """
        return patch.object(
            type(self.env["llm.tool"]),
            "execute",
            autospec=True,
            return_value={"ok": True},
        )

    def _make_thread(self, tools):
        return self.env["llm.thread"].create(
            {
                "name": "Consent Thread",
                "provider_id": self.provider.id,
                "model_id": self.model.id,
                "tool_ids": [(6, 0, tools.ids)],
            }
        )

    def _tool_call(self, name, call_id="call_1"):
        return {
            "id": call_id,
            "type": "function",
            "function": {"name": name, "arguments": "{}"},
        }

    def _run_tool_call(self, thread, tool, call_id="call_1"):
        """Post a tool call and drive it through execute_tool_call()."""
        msg = self.Message.post_tool_call(
            self._tool_call(tool.name, call_id), thread_model=thread
        )
        list(msg.execute_tool_call(thread_model=thread))
        return msg


@tagged("post_install", "-at_install")
class TestToolConsentEnforcement(ConsentCase):
    # -- 1. a consent-required tool is held, and does not run ---------------

    def test_consent_required_tool_does_not_execute(self):
        tool = self._make_tool("consent_tool")
        thread = self._make_thread(tool)

        with patch.object(
            type(self.env["llm.tool"]), "execute", autospec=True
        ) as executed:
            msg = self._run_tool_call(thread, tool)
            executed.assert_not_called()

        self.assertTrue(msg.is_pending_consent())
        self.assertIsNone(msg.get_consent_decision())
        self.assertNotIn("result", msg.get_tool_data())

    # -- 2. executes after an explicit grant, recording who and when --------

    def test_executes_after_grant(self):
        tool = self._make_tool("consent_tool_grant")
        thread = self._make_thread(tool)
        msg = self._run_tool_call(thread, tool)
        self.assertTrue(msg.is_pending_consent())

        msg.grant_tool_consent()

        consent = msg.get_tool_data()["consent"]
        self.assertEqual(consent["decision"], "granted")
        self.assertEqual(consent["user_id"], self.env.uid)
        self.assertEqual(consent["user_login"], self.env.user.login)
        self.assertTrue(consent["date"])
        self.assertEqual(msg.get_tool_data()["status"], "requested")

        with self._patched_execute() as executed:
            list(msg.execute_tool_call(thread_model=thread))
            executed.assert_called_once()
        self.assertEqual(msg.get_tool_data()["status"], "completed")

    # -- 3. denial records the decision and answers the model ---------------

    def test_denial_records_decision_and_writes_result(self):
        tool = self._make_tool("consent_tool_deny")
        thread = self._make_thread(tool)

        with patch.object(
            type(self.env["llm.tool"]), "execute", autospec=True
        ) as executed:
            msg = self._run_tool_call(thread, tool)
            msg.deny_tool_consent()
            executed.assert_not_called()

        data = msg.get_tool_data()
        self.assertEqual(data["status"], "denied")
        self.assertEqual(data["consent"]["decision"], "denied")
        self.assertEqual(data["consent"]["user_id"], self.env.uid)
        # Providers serialise tool_data["result"] back to the model, so a
        # refused call must still answer or the conversation stalls. It is a
        # plain instruction string, not an error object: an error invites the
        # model to retry the same call, which is what the gate is for.
        self.assertIn("result", data)
        self.assertIsInstance(data["result"], str)
        self.assertNotIn("error", data["result"].lower())
        self.assertIn("declined", data["result"])
        self.assertIn("Do not call it again", data["result"])

    # -- 3b. the gate holds if the model calls the tool again ---------------

    def test_gate_holds_on_repeat_call_after_denial(self):
        """A denial does not unlock the tool.

        The instruction string asks the model not to retry, but the gate must
        not depend on the model obeying it: a second identical call is held
        exactly like the first.
        """
        tool = self._make_tool("consent_tool_repeat")
        thread = self._make_thread(tool)

        with patch.object(
            type(self.env["llm.tool"]), "execute", autospec=True
        ) as executed:
            first = self._run_tool_call(thread, tool, "call_first")
            first.deny_tool_consent()

            # The model ignores the instruction and calls the same tool again.
            second = self._run_tool_call(thread, tool, "call_second")

            executed.assert_not_called()

        self.assertEqual(first.get_tool_data()["status"], "denied")
        self.assertTrue(second.is_pending_consent())
        self.assertIsNone(second.get_consent_decision())
        self.assertNotIn("result", second.get_tool_data())

    # -- 4. a tool without the flag is untouched ----------------------------

    def test_non_consent_tool_executes_directly(self):
        tool = self._make_tool("plain_tool", requires_consent=False)
        thread = self._make_thread(tool)

        with self._patched_execute() as executed:
            msg = self._run_tool_call(thread, tool)
            executed.assert_called_once()

        self.assertFalse(msg.is_pending_consent())
        self.assertEqual(msg.get_tool_data()["status"], "completed")
        self.assertIsNone(msg.get_consent_decision())

    # -- 5. granting twice is harmless --------------------------------------

    def test_grant_is_idempotent(self):
        tool = self._make_tool("consent_tool_twice")
        thread = self._make_thread(tool)
        msg = self._run_tool_call(thread, tool)

        msg.grant_tool_consent()
        first = msg.get_tool_data()["consent"]["date"]
        msg.grant_tool_consent()

        self.assertEqual(msg.get_tool_data()["consent"]["date"], first)


@tagged("post_install", "-at_install")
class TestToolConsentThreadFlow(ConsentCase):
    """Loop behaviour: pausing, resuming, the text shortcut, parallel calls."""

    def _post_user(self, thread, body):
        return thread.message_post(
            body=body, llm_role="user", author_id=self.env.user.partner_id.id
        )

    # -- 6. the loop stops while a call is pending --------------------------

    def test_should_continue_is_false_while_pending(self):
        tool = self._make_tool("loop_tool")
        thread = self._make_thread(tool)
        msg = self._run_tool_call(thread, tool, "call_loop")

        self.assertTrue(msg.is_pending_consent())
        self.assertFalse(thread._should_continue(msg))

    # -- 7. the loop resumes once a denial is recorded ----------------------

    def test_loop_resumes_after_denial(self):
        tool = self._make_tool("deny_resume_tool")
        thread = self._make_thread(tool)
        msg = self._run_tool_call(thread, tool, "call_deny_resume")
        self.assertFalse(thread._should_continue(msg))

        msg.deny_tool_consent()

        self.assertFalse(msg.is_pending_consent())
        self.assertTrue(thread._should_continue(msg))

    # -- 8. "continue" with nothing pending is an ordinary message ----------

    def test_continue_without_pending_call_is_ordinary_message(self):
        tool = self._make_tool("no_pending_tool")
        thread = self._make_thread(tool)
        user_msg = self._post_user(thread, "continue")

        result = list(thread._resume_pending_tool_consent(user_msg))

        self.assertFalse(thread._get_pending_consent_messages())
        self.assertEqual(result, [])

    # -- 9. an ambiguous reply leaves the call pending ----------------------

    def test_ambiguous_reply_leaves_call_pending(self):
        tool = self._make_tool("ambiguous_tool")
        thread = self._make_thread(tool)
        msg = self._run_tool_call(thread, tool, "call_ambiguous")

        user_msg = self._post_user(thread, "no, don't do that yet")
        list(thread._resume_pending_tool_consent(user_msg))

        self.assertTrue(msg.is_pending_consent())
        self.assertIsNone(msg.get_consent_decision())

    # -- 10. one decision covers every pending call in the turn -------------

    def test_text_decision_applies_to_all_pending_calls(self):
        consent_a = self._make_tool("parallel_a")
        consent_b = self._make_tool("parallel_b")
        plain = self._make_tool("parallel_plain", requires_consent=False)
        thread = self._make_thread(consent_a | consent_b | plain)

        with self._patched_execute():
            msg_a = self._run_tool_call(thread, consent_a, "call_a")
            msg_b = self._run_tool_call(thread, consent_b, "call_b")
            msg_plain = self._run_tool_call(thread, plain, "call_plain")

        self.assertTrue(msg_a.is_pending_consent())
        self.assertTrue(msg_b.is_pending_consent())
        self.assertEqual(msg_plain.get_tool_data()["status"], "completed")

        user_msg = self._post_user(thread, "no")
        list(thread._resume_pending_tool_consent(user_msg))

        self.assertEqual(msg_a.get_consent_decision(), "denied")
        self.assertEqual(msg_b.get_consent_decision(), "denied")
        # the call that already completed in that turn is left alone
        self.assertEqual(msg_plain.get_tool_data()["status"], "completed")
        self.assertIsNone(msg_plain.get_consent_decision())
