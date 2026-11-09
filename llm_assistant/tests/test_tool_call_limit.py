# Copyright 2026 Lijo Antony
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html).

from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestToolCallLimit(TransactionCase):
    def setUp(self):
        super().setUp()
        prompt = self.env["llm.prompt"].create(
            {"name": "Tool limit prompt", "template": "Run the requested tools."}
        )
        self.assistant = self.env["llm.assistant"].create(
            {"name": "Tool limit test", "prompt_id": prompt.id, "tool_calls_max": 2}
        )
        self.tool = self.env["llm.tool"].create(
            {
                "name": "tool_limit_probe",
                "description": "Return a synthetic result",
                "implementation": "function",
                "read_only_hint": True,
            }
        )
        provider_model = self.env["llm.provider"]
        with patch.object(
            type(provider_model),
            "_get_available_services",
            return_value=[("test", "Test")],
        ):
            provider = provider_model.create(
                {"name": "Tool limit provider", "service": "test"}
            )
        model = self.env["llm.model"].create(
            {"name": "test-model", "provider_id": provider.id, "model_use": "chat"}
        )
        self.thread = self.env["llm.thread"].create(
            {
                "name": "Tool limit test",
                "assistant_id": self.assistant.id,
                "provider_id": provider.id,
                "model_id": model.id,
                "tool_ids": [(6, 0, self.tool.ids)],
            }
        )

    def _run_turn(self, batch_sizes, last_message=None):
        batches = iter(batch_sizes)
        executed = []
        generated = []
        if last_message is None:
            last_message = self.thread.message_post(body="Run tools", llm_role="user")

        def generate(thread):
            generated.append(True)
            size = next(batches, 0)
            calls = [
                {
                    "id": f"call_{len(generated)}_{n}",
                    "type": "function",
                    "function": {"name": "tool_limit_probe", "arguments": "{}"},
                }
                for n in range(size)
            ]
            return (
                yield from thread._handle_non_streaming_response(
                    {"tool_calls": calls} if calls else {"content": "Done"}
                )
            )

        def execute(tool, parameters):
            executed.append(tool.env.context["message"].body_json["tool_call_id"])
            return {"ok": True}

        events = []
        with (
            patch.object(type(self.thread), "_generate_assistant_response", generate),
            patch.object(type(self.tool), "execute", execute),
            patch.object(self.env.cr, "commit"),
        ):
            generator = self.thread.generate_messages(last_message)
            while True:
                try:
                    events.append(next(generator))
                except StopIteration as done:
                    result = done.value
                    break
        self.assertEqual(
            sum(event["type"] == "tool_succeeded" for event in events), len(executed)
        )
        return executed, generated, events, result

    def test_cap_stops_inside_one_large_batch(self):
        executed, generated, events, result = self._run_turn([4])
        self.assertEqual(len(executed), 2)
        self.assertEqual(len(generated), 1)
        self.assertIn("Tool call limit reached", str(result.body))
        self.assertEqual(events[-1]["type"], "message_create")

    def test_cap_counts_across_batches(self):
        executed, generated, events, result = self._run_turn([1, 1, 1])
        self.assertEqual(len(executed), 2)
        self.assertEqual(len(generated), 2)
        self.assertIn("Stopped after 2 tool calls", str(result.body))

    def test_under_limit_allows_final_answer(self):
        executed, generated, events, result = self._run_turn([1, 0])
        self.assertEqual(len(executed), 1)
        self.assertEqual(len(generated), 2)
        self.assertIn("Done", str(result.body))

    def test_zero_limit_and_no_assistant_allow_tools(self):
        self.assistant.tool_calls_max = 0
        executed, generated, events, result = self._run_turn([4, 0])
        self.assertEqual(len(executed), 4)
        self.thread.assistant_id = False
        executed, generated, events, result = self._run_turn([4, 0])
        self.assertEqual(len(executed), 4)

    def test_new_turn_resets_count(self):
        self._run_turn([3])
        executed, generated, events, result = self._run_turn([3])
        self.assertEqual(len(executed), 2)

    def test_assistant_batch_entry_uses_same_limit(self):
        calls = [
            {
                "id": f"entry_{n}",
                "type": "function",
                "function": {"name": "tool_limit_probe", "arguments": "{}"},
            }
            for n in range(4)
        ]
        message = self.thread.message_post(
            body="", llm_role="assistant", body_json={"tool_calls": calls}
        )
        executed, generated, events, result = self._run_turn([], last_message=message)
        self.assertEqual(len(executed), 2)
        self.assertEqual(len(generated), 0)

    def test_skipped_calls_have_matching_error_results(self):
        calls = [
            {
                "id": f"batch_{n}",
                "type": "function",
                "function": {"name": "tool_limit_probe", "arguments": "{}"},
            }
            for n in range(4)
        ]
        message = self.thread.message_post(
            body="", llm_role="assistant", body_json={"tool_calls": calls}
        )
        executed, generated, events, result = self._run_turn([], last_message=message)
        self.assertEqual(len(executed), 2)
        results = {
            item.body_json["tool_call_id"]: item.body_json["status"]
            for item in self.thread.message_ids.filtered(
                lambda item: item.llm_role == "tool"
            )
        }
        self.assertEqual(
            results,
            {
                "batch_0": "completed",
                "batch_1": "completed",
                "batch_2": "error",
                "batch_3": "error",
            },
        )
