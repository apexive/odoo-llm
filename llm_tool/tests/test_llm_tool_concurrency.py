"""
Test tool registration: in-memory scan + raw SQL sync.

_register_hook populates _tool_registry (no DB writes).
_sync_tools_to_db writes via raw SQL with advisory lock.
action_sync_tools wraps _sync_tools_to_db with UI notification.
"""

from odoo.tests import common


class TestLLMToolSync(common.TransactionCase):
    """Test the tool sync mechanism."""

    def setUp(self):
        super().setUp()
        self.LLMTool = self.env["llm.tool"]

    def _create_tool(self, name, model="res.partner", method=None, **kw):
        """Helper: create a function tool in DB."""
        return self.LLMTool.create(
            {
                "name": name,
                "description": kw.pop("description", f"Desc for {name}"),
                "implementation": "function",
                "decorator_model": model,
                "decorator_method": method or name,
                **kw,
            }
        )

    # -- _sync_tools_to_db (raw SQL) --

    def test_sync_creates_new_tool(self):
        self.LLMTool._tool_registry = {
            ("res.partner", "new_method"): {
                "name": "new_tool",
                "implementation": "function",
                "decorator_model": "res.partner",
                "decorator_method": "new_method",
                "description": "A new tool",
                "active": True,
            }
        }
        self.LLMTool._xml_managed_keys = set()

        result = self.LLMTool._sync_tools_to_db()

        self.assertEqual(result["created"], 1)
        tool = self.LLMTool.search([("name", "=", "new_tool")])
        self.assertTrue(tool)
        self.assertEqual(tool.description, "A new tool")

    def test_sync_updates_changed_tool(self):
        self._create_tool("upd_tool", method="upd_method", description="Old")

        self.LLMTool._tool_registry = {
            ("res.partner", "upd_method"): {
                "name": "upd_tool",
                "implementation": "function",
                "decorator_model": "res.partner",
                "decorator_method": "upd_method",
                "description": "New",
                "active": True,
            }
        }
        self.LLMTool._xml_managed_keys = set()
        self.LLMTool.invalidate_model()

        result = self.LLMTool._sync_tools_to_db()

        self.assertEqual(result["updated"], 1)
        tool = self.LLMTool.search([("name", "=", "upd_tool")])
        self.assertEqual(tool.description, "New")

    def test_sync_noop_when_unchanged(self):
        self._create_tool("same_tool", method="same_method", description="Same")

        self.LLMTool._tool_registry = {
            ("res.partner", "same_method"): {
                "name": "same_tool",
                "implementation": "function",
                "decorator_model": "res.partner",
                "decorator_method": "same_method",
                "description": "Same",
                "active": True,
            }
        }
        self.LLMTool._xml_managed_keys = set()
        self.LLMTool.invalidate_model()

        result = self.LLMTool._sync_tools_to_db()

        self.assertEqual(result["created"], 0)
        self.assertEqual(result["updated"], 0)
        self.assertEqual(result["deactivated"], 0)

    def test_sync_deactivates_missing_tool(self):
        tool = self._create_tool("orphan", method="orphan_method")
        self.LLMTool._tool_registry = {}
        self.LLMTool._xml_managed_keys = set()
        self.LLMTool.invalidate_model()

        result = self.LLMTool._sync_tools_to_db()

        self.assertEqual(result["deactivated"], 1)
        tool.invalidate_recordset()
        self.assertFalse(tool.active)

    def test_sync_skips_xml_managed_deactivation(self):
        tool = self._create_tool("xml_tool", method="xml_method")
        self.LLMTool._tool_registry = {}
        self.LLMTool._xml_managed_keys = {("res.partner", "xml_method")}
        self.LLMTool.invalidate_model()

        result = self.LLMTool._sync_tools_to_db()

        self.assertEqual(result["deactivated"], 0)
        tool.invalidate_recordset()
        self.assertTrue(tool.active)

    def test_sync_respects_auto_update_false(self):
        self._create_tool(
            "locked_tool",
            method="locked_method",
            description="Manual",
            auto_update=False,
        )
        self.LLMTool._tool_registry = {
            ("res.partner", "locked_method"): {
                "name": "locked_tool",
                "implementation": "function",
                "decorator_model": "res.partner",
                "decorator_method": "locked_method",
                "description": "Decorator says different",
                "active": True,
            }
        }
        self.LLMTool._xml_managed_keys = set()
        self.LLMTool.invalidate_model()

        result = self.LLMTool._sync_tools_to_db()

        self.assertEqual(result["updated"], 0)
        tool = self.LLMTool.search([("name", "=", "locked_tool")])
        self.assertEqual(tool.description, "Manual")

    # -- action_sync_tools (button) --

    def test_action_empty_registry(self):
        self.LLMTool._tool_registry = {}
        result = self.LLMTool.action_sync_tools()
        self.assertEqual(result["params"]["type"], "warning")

    def test_action_already_in_sync(self):
        self._create_tool("btn_tool", method="btn_method", description="OK")
        self.LLMTool._tool_registry = {
            ("res.partner", "btn_method"): {
                "name": "btn_tool",
                "implementation": "function",
                "decorator_model": "res.partner",
                "decorator_method": "btn_method",
                "description": "OK",
                "active": True,
            }
        }
        self.LLMTool._xml_managed_keys = set()
        self.LLMTool.invalidate_model()

        result = self.LLMTool.action_sync_tools()
        self.assertIn("Already in sync", result["params"]["title"])

    def test_action_reports_changes(self):
        self.LLMTool._tool_registry = {
            ("res.partner", "action_new"): {
                "name": "action_new_tool",
                "implementation": "function",
                "decorator_model": "res.partner",
                "decorator_method": "action_new",
                "description": "Via button",
                "active": True,
            }
        }
        self.LLMTool._xml_managed_keys = set()

        result = self.LLMTool.action_sync_tools()
        self.assertEqual(result["params"]["type"], "success")

    # -- _register_hook & helpers --

    def test_register_hook_populates_registry(self):
        self.LLMTool._tool_registry.clear()
        self.LLMTool._xml_managed_keys.clear()
        self.LLMTool._register_hook()
        self.assertIsInstance(self.LLMTool._tool_registry, dict)
        self.assertIsInstance(self.LLMTool._xml_managed_keys, set)

    def test_extract_tool_values(self):
        def mock(self):
            """Mock desc"""

        mock._llm_tool_name = "my_tool"
        mock._llm_tool_description = "My tool"
        mock._llm_tool_metadata = {"read_only_hint": True, "idempotent_hint": True}

        values = self.LLMTool._extract_tool_values("res.partner", "mock", mock)

        self.assertEqual(values["name"], "my_tool")
        self.assertEqual(values["description"], "My tool")
        self.assertTrue(values["read_only_hint"])
        self.assertTrue(values["idempotent_hint"])
        self.assertNotIn("destructive_hint", values)

    def test_raw_values_changed_detects_difference(self):
        db_row = {"name": "old", "description": "old desc", "active": True}
        values = {
            "name": "old",
            "description": "new desc",
            "active": True,
        }
        self.assertTrue(self.LLMTool._raw_values_changed(db_row, values))

    def test_raw_values_changed_ignores_none_vs_empty(self):
        db_row = {"name": "t", "description": None, "active": True}
        values = {"name": "t", "description": "", "active": True}
        self.assertFalse(self.LLMTool._raw_values_changed(db_row, values))
