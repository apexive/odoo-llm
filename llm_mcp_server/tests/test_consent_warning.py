"""The MCP path is not gated by the chat-path consent check -- it must say so.

execute_mcp_tool() calls llm.tool.execute() directly and never passes through
mail.message.execute_tool_call(), so the consent gate added for the chat path
does not apply. That is deliberate (no interactive Odoo user in an MCP request;
MCP hosts run their own approval UI), but it must not be silent. See issue #86.
"""

from unittest.mock import patch

from odoo.tests import common, tagged


@tagged("post_install", "-at_install")
class TestMCPConsentWarning(common.TransactionCase):
    def _make_tool(self, name, requires_consent):
        return self.env["llm.tool"].create(
            {
                "name": name,
                "description": f"Test tool {name}",
                "implementation": "function",
                "decorator_model": "res.partner",
                "decorator_method": "read",
                "requires_user_consent": requires_consent,
                "active": True,
            }
        )

    def test_consent_required_tool_over_mcp_logs_warning(self):
        tool = self._make_tool("mcp_consent_tool", True)

        with patch.object(type(tool), "execute", autospec=True, return_value={}):
            with self.assertLogs(
                "odoo.addons.llm_mcp_server.models.llm_tool", level="WARNING"
            ) as logs:
                self.env["llm.tool"].execute_mcp_tool(
                    {"name": tool.name, "arguments": {}}
                )

        joined = "\n".join(logs.output)
        self.assertIn("consent-required tool", joined)
        self.assertIn(tool.name, joined)

    def test_plain_tool_over_mcp_logs_no_warning(self):
        tool = self._make_tool("mcp_plain_tool", False)

        with patch.object(type(tool), "execute", autospec=True, return_value={}):
            with self.assertNoLogs(
                "odoo.addons.llm_mcp_server.models.llm_tool", level="WARNING"
            ):
                self.env["llm.tool"].execute_mcp_tool(
                    {"name": tool.name, "arguments": {}}
                )
