"""
llm.tool extension for implementation='mcp_client'

Plugs into the existing _get_available_implementations() hook so that
the tool selection dropdown gains a new "External MCP Server" option.
When tool.execute() is called the call is proxied to the remote server.
"""

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class LLMTool(models.Model):
    _inherit = "llm.tool"

    # ── New fields ─────────────────────────────────────────────────────────────

    mcp_server_id = fields.Many2one(
        "llm.mcp.client.server",
        string="MCP Server",
        ondelete="restrict",
        help="Remote MCP server this tool belongs to.",
    )
    mcp_tool_name = fields.Char(
        string="Remote Tool Name",
        help="The tool name as advertised by the remote MCP server (tools/list).",
    )

    # ── Implementation hook ────────────────────────────────────────────────────

    @api.model
    def _get_available_implementations(self):
        impls = super()._get_available_implementations()
        return impls + [("mcp_client", "External MCP Server")]

    # ── Execution ──────────────────────────────────────────────────────────────

    def execute(self, parameters):
        """Override execute() for mcp_client tools.

        The base execute() builds a Pydantic model from mcp_client_execute(**kwargs),
        making Pydantic expect a literal 'kwargs' field — breaking all mcp_client calls.

        For mcp_client, bypass signature introspection and pass parameters directly.
        """
        if self.implementation == "mcp_client":
            self.ensure_one()
            return self.mcp_client_execute(**parameters)
        return super().execute(parameters)

    def mcp_client_execute(self, **kwargs):
        """
        Execute this tool by proxying the call to the remote MCP server.

        Called automatically by llm.tool._get_implementation_method() when
        implementation == 'mcp_client', which in turn is invoked by
        llm.tool.execute(parameters).
        """
        self.ensure_one()

        if not self.mcp_server_id:
            raise UserError(
                _("Tool '%(tool)s' has no MCP server configured.")
                % {"tool": self.name}
            )
        if not self.mcp_tool_name:
            raise UserError(
                _("Tool '%(tool)s' has no remote tool name configured.")
                % {"tool": self.name}
            )

        # kwargs are the validated parameters forwarded from execute()
        _logger.debug(
            "Proxying tool call '%s' → %s/%s with args: %s",
            self.name,
            self.mcp_server_id.name,
            self.mcp_tool_name,
            kwargs,
        )

        return self.mcp_server_id.call_tool(self.mcp_tool_name, kwargs)

    # ── Override execute() to support mcp_client without a Python method ──────

    def _get_implementation_method(self):
        """
        Override to handle mcp_client implementation which has no decorator_method.
        For mcp_client we return the bound mcp_client_execute method directly.
        """
        self.ensure_one()

        if self.implementation == "mcp_client":
            return self.mcp_client_execute

        return super()._get_implementation_method()

    # ── Override get_input_schema for mcp_client ──────────────────────────────

    def get_input_schema(self):
        """
        For mcp_client tools the schema is always stored in the DB field
        (populated during sync).  Skip the MCP SDK introspection path.
        """
        self.ensure_one()

        if self.implementation == "mcp_client":
            if self.input_schema:
                import json
                return json.loads(self.input_schema)
            # Return a permissive empty schema if nothing was synced
            return {"type": "object", "properties": {}}

        return super().get_input_schema()
