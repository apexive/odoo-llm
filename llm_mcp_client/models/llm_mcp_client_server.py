"""
llm.mcp.client.server  —  Remote MCP server connection + tool sync
"""

import json
import logging

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# MCP JSON-RPC constants
JSONRPC_VERSION = "2.0"
MCP_PROTOCOL_VERSION = "2025-06-18"
DEFAULT_TIMEOUT = 30  # seconds


class LLMMcpClientServer(models.Model):
    """
    Represents a remote MCP server that Odoo can consume tools from.

    Lifecycle
    ---------
    1. Create a record with URL + optional auth.
    2. Click "Test Connection" to verify reachability.
    3. Click "Sync Tools" to import remote tools as llm.tool records
       with implementation='mcp_client'.
    4. Assign those llm.tool records to assistants / threads as usual.
    """

    _name = "llm.mcp.client.server"
    _description = "Remote MCP Server (Client)"
    _inherit = ["mail.thread"]
    _order = "name"

    # ── Basic info ────────────────────────────────────────────────────────────

    name = fields.Char(
        required=True,
        tracking=True,
        help="Human-readable name shown in tool form and assistant config.",
    )
    active = fields.Boolean(default=True, tracking=True)
    url = fields.Char(
        string="MCP Endpoint URL",
        required=True,
        tracking=True,
        help="Full URL of the remote MCP server endpoint, e.g. https://mcp.example.com/mcp",
    )
    description = fields.Text(
        help="Optional notes about what this server provides.",
    )

    # ── Authentication ────────────────────────────────────────────────────────

    auth_type = fields.Selection(
        [
            ("none", "No Authentication"),
            ("bearer", "Bearer Token"),
        ],
        default="none",
        required=True,
        tracking=True,
    )
    token = fields.Char(
        string="Bearer Token",
        help="Token sent as 'Authorization: Bearer <token>' header.",
    )

    # ── Transport / connection ────────────────────────────────────────────────

    timeout = fields.Integer(
        default=DEFAULT_TIMEOUT,
        help="HTTP request timeout in seconds.",
    )

    # ── Sync metadata ─────────────────────────────────────────────────────────

    last_sync_date = fields.Datetime(
        string="Last Synced",
        readonly=True,
    )
    sync_status = fields.Selection(
        [
            ("never", "Never Synced"),
            ("ok", "OK"),
            ("error", "Error"),
        ],
        default="never",
        readonly=True,
        tracking=True,
    )
    sync_error = fields.Text(
        string="Last Sync Error",
        readonly=True,
    )
    tool_count = fields.Integer(
        string="Tools",
        compute="_compute_tool_count",
    )
    tool_ids = fields.One2many(
        "llm.tool",
        "mcp_server_id",
        string="Synced Tools",
        domain=[("implementation", "=", "mcp_client")],
    )

    # ── Computed ──────────────────────────────────────────────────────────────

    def _compute_tool_count(self):
        for server in self:
            server.tool_count = self.env["llm.tool"].search_count(
                [
                    ("mcp_server_id", "=", server.id),
                    ("implementation", "=", "mcp_client"),
                ]
            )

    # ── Low-level HTTP helpers ────────────────────────────────────────────────

    def _build_headers(self):
        """Return HTTP headers for calls to this server."""
        self.ensure_one()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
        }
        if self.auth_type == "bearer" and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _jsonrpc_call(self, method, params=None, req_id=1):
        """
        Send a single JSON-RPC 2.0 request to the remote MCP server.

        Returns the 'result' field of the response, or raises UserError on
        transport / protocol error.
        """
        self.ensure_one()
        payload = {
            "jsonrpc": JSONRPC_VERSION,
            "id": req_id,
            "method": method,
            "params": params or {},
        }
        try:
            resp = requests.post(
                self.url,
                json=payload,
                headers=self._build_headers(),
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except requests.exceptions.Timeout:
            raise UserError(
                _("Connection to MCP server '%(name)s' timed out after %(t)d seconds.")
                % {"name": self.name, "t": self.timeout}
            )
        except requests.exceptions.ConnectionError as e:
            raise UserError(
                _("Cannot reach MCP server '%(name)s': %(err)s")
                % {"name": self.name, "err": str(e)}
            )
        except requests.exceptions.HTTPError as e:
            raise UserError(
                _("HTTP error from MCP server '%(name)s': %(err)s")
                % {"name": self.name, "err": str(e)}
            )

        try:
            data = resp.json()
        except ValueError:
            raise UserError(
                _("MCP server '%(name)s' returned non-JSON response: %(body)s")
                % {"name": self.name, "body": resp.text[:200]}
            )

        if "error" in data:
            err = data["error"]
            raise UserError(
                _("MCP server '%(name)s' returned error %(code)s: %(msg)s")
                % {
                    "name": self.name,
                    "code": err.get("code", "?"),
                    "msg": err.get("message", ""),
                }
            )

        return data.get("result", {})

    # ── Public API ────────────────────────────────────────────────────────────

    def action_test_connection(self):
        """Send a ping to the remote server and show a notification."""
        self.ensure_one()
        try:
            # First initialize so the server accepts further calls
            self._mcp_initialize()
            self._jsonrpc_call("ping", req_id=2)
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Connection OK"),
                    "message": _("Successfully connected to '%s'.") % self.name,
                    "type": "success",
                    "sticky": False,
                },
            }
        except UserError as e:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Connection Failed"),
                    "message": str(e),
                    "type": "danger",
                    "sticky": True,
                },
            }

    def action_sync_tools(self):
        """
        Fetch tools/list from the remote server and upsert llm.tool records.

        Strategy
        --------
        • Tools that exist and haven't changed → left alone.
        • Tools that exist but changed → name/description/schema updated.
        • New tools on server → created.
        • Tools that were previously synced from this server but are no longer
          returned → deactivated (not deleted).
        """
        self.ensure_one()
        try:
            result = self._fetch_tools_list()
            stats = self._upsert_tools(result)
            # Persist sync metadata
            self.write(
                {
                    "last_sync_date": fields.Datetime.now(),
                    "sync_status": "ok",
                    "sync_error": False,
                }
            )
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Sync Complete"),
                    "message": _(
                        "%(created)d created, %(updated)d updated, %(deactivated)d deactivated."
                    )
                    % stats,
                    "type": "success",
                    "sticky": False,
                    "next": {"type": "ir.actions.client", "tag": "reload"},
                },
            }
        except Exception as e:
            _logger.exception("MCP tool sync failed for server %s", self.name)
            self.write(
                {
                    "last_sync_date": fields.Datetime.now(),
                    "sync_status": "error",
                    "sync_error": str(e),
                }
            )
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Sync Failed"),
                    "message": str(e),
                    "type": "danger",
                    "sticky": True,
                },
            }

    def action_view_tools(self):
        """Open the list of tools synced from this server."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Tools — %s") % self.name,
            "res_model": "llm.tool",
            "view_mode": "list,form",
            "domain": [
                ("mcp_server_id", "=", self.id),
                ("implementation", "=", "mcp_client"),
            ],
            "context": {"default_mcp_server_id": self.id},
        }

    # ── MCP protocol helpers ──────────────────────────────────────────────────

    def _mcp_initialize(self):
        """
        Send MCP initialize request.  Some servers require this before
        tools/list; others accept tools/list directly.  We call it as a
        best-effort step and swallow errors so sync still works on lenient
        servers.
        """
        self.ensure_one()
        try:
            self._jsonrpc_call(
                "initialize",
                params={
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "clientInfo": {
                        "name": "Odoo LLM MCP Client",
                        "version": "18.0.1.0.0",
                    },
                    "capabilities": {},
                },
                req_id=1,
            )
        except UserError as e:
            _logger.debug(
                "MCP initialize failed for %s (may be stateless): %s", self.name, e
            )

    def _fetch_tools_list(self):
        """
        Call tools/list on the remote server.

        Returns a list of tool dicts with at minimum:
            { "name": str, "description": str, "inputSchema": dict }
        """
        self.ensure_one()
        self._mcp_initialize()
        result = self._jsonrpc_call("tools/list", req_id=3)
        tools = result.get("tools", [])
        if not isinstance(tools, list):
            raise UserError(
                _("Unexpected tools/list response from '%(name)s': %(data)s")
                % {"name": self.name, "data": str(result)[:200]}
            )
        return tools

    def call_tool(self, tool_name, arguments):
        """
        Execute a tool on the remote server via tools/call.

        Args:
            tool_name (str): The MCP tool name (as returned by tools/list).
            arguments (dict): The parsed arguments to pass.

        Returns:
            str: Text content extracted from the MCP CallToolResult.

        Raises:
            UserError: On connection / protocol / remote execution error.
        """
        self.ensure_one()
        result = self._jsonrpc_call(
            "tools/call",
            params={"name": tool_name, "arguments": arguments},
            req_id=10,
        )
        # MCP CallToolResult: { "content": [{"type": "text", "text": "..."}], "isError": bool }
        is_error = result.get("isError", False)
        content_blocks = result.get("content", [])
        text = "\n".join(
            block.get("text", "")
            for block in content_blocks
            if block.get("type") == "text"
        )
        if is_error:
            raise UserError(
                _("Remote MCP tool '%(tool)s' on '%(server)s' returned an error: %(msg)s")
                % {"tool": tool_name, "server": self.name, "msg": text}
            )
        return text

    # ── Tool upsert logic ─────────────────────────────────────────────────────

    def _upsert_tools(self, remote_tools):
        """
        Sync a list of MCP tool definitions into llm.tool records.

        Returns dict with keys: created, updated, deactivated.
        """
        self.ensure_one()
        Tool = self.env["llm.tool"]

        # Index existing mcp_client tools for this server by mcp_tool_name
        existing = Tool.search(
            [("mcp_server_id", "=", self.id), ("implementation", "=", "mcp_client")]
        )
        existing_by_mcp_name = {t.mcp_tool_name: t for t in existing}

        remote_names = set()
        created = updated = 0

        for tool_def in remote_tools:
            mcp_name = tool_def.get("name", "").strip()
            if not mcp_name:
                _logger.warning("Skipping tool with no name from server %s", self.name)
                continue

            remote_names.add(mcp_name)
            description = tool_def.get("description", "") or ""
            input_schema = tool_def.get("inputSchema") or {}

            # Build values for create/update
            vals = {
                "name": f"{self.name}/{mcp_name}",
                "mcp_tool_name": mcp_name,
                "description": description,
                "implementation": "mcp_client",
                "mcp_server_id": self.id,
                "input_schema": json.dumps(input_schema, indent=2) if input_schema else False,
                "active": True,
                # Sensible defaults from MCP annotations if present
                "read_only_hint": tool_def.get("annotations", {}).get("readOnlyHint", False),
                "destructive_hint": tool_def.get("annotations", {}).get("destructiveHint", True),
                "idempotent_hint": tool_def.get("annotations", {}).get("idempotentHint", False),
                "open_world_hint": tool_def.get("annotations", {}).get("openWorldHint", True),
            }

            existing_tool = existing_by_mcp_name.get(mcp_name)
            if existing_tool:
                # Update only if something changed
                if self._tool_changed(existing_tool, vals):
                    existing_tool.write(vals)
                    updated += 1
            else:
                Tool.create(vals)
                created += 1

        # Deactivate tools that are no longer advertised by the server
        deactivated = 0
        for mcp_name, tool in existing_by_mcp_name.items():
            if mcp_name not in remote_names and tool.active:
                tool.write({"active": False})
                deactivated += 1

        _logger.info(
            "MCP tool sync for '%s': %d created, %d updated, %d deactivated",
            self.name,
            created,
            updated,
            deactivated,
        )
        return {"created": created, "updated": updated, "deactivated": deactivated}

    @staticmethod
    def _tool_changed(tool, vals):
        """Return True if any relevant field differs from stored values."""
        check_fields = ("name", "description", "input_schema", "active")
        for f in check_fields:
            stored = getattr(tool, f, None) or False
            new = vals.get(f) or False
            if stored != new:
                return True
        return False
