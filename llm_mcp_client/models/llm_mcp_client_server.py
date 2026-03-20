"""
llm.mcp.client.server  —  Remote MCP server connection + tool sync

Supports two transports:
  • http   — JSON-RPC over HTTP POST (bearer token auth optional)
  • stdio  — JSON-RPC over stdin/stdout (local process, e.g. npx @upstash/context7-mcp)
"""

import json
import logging
import re
import subprocess

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
    Represents an MCP server that Odoo can consume tools from.

    Two transports are supported:

    HTTP transport
    --------------
    Fill in the URL field.  Optionally add a Bearer token.
    Used for remote servers (SaaS, another Odoo instance, etc.).

    Stdio transport
    ---------------
    Fill in the Command field (e.g. ``npx``) and Args (e.g. ``-y @upstash/context7-mcp``).
    Odoo will spawn the process on every call and communicate over stdin/stdout.
    Used for local MCP servers distributed as npm packages or executables.

    Example — Context7:
        Transport : stdio
        Command   : npx
        Args      : -y @upstash/context7-mcp
    """

    _name = "llm.mcp.client.server"
    _description = "Remote MCP Server (Client)"
    _inherit = ["mail.thread"]
    _order = "name"

    # ── Basic info ────────────────────────────────────────────────────────────

    name = fields.Char(
        required=True,
        tracking=True,
    )
    active = fields.Boolean(default=True, tracking=True)
    description = fields.Text()

    # ── Transport ─────────────────────────────────────────────────────────────

    transport = fields.Selection(
        [
            ("http", "HTTP"),
            ("stdio", "Stdio (local process)"),
        ],
        default="http",
        required=True,
        tracking=True,
        help=(
            "HTTP: connect to a remote MCP server via HTTP POST.\n"
            "Stdio: spawn a local process and communicate via stdin/stdout."
        ),
    )

    # HTTP-specific fields
    url = fields.Char(
        string="MCP Endpoint URL",
        tracking=True,
        help="Full URL of the HTTP MCP endpoint, e.g. https://mcp.example.com/mcp",
    )
    auth_type = fields.Selection(
        [
            ("none", "No Authentication"),
            ("bearer", "Bearer Token"),
        ],
        default="none",
        tracking=True,
    )
    token = fields.Char(
        string="Bearer Token",
        help="Sent as 'Authorization: Bearer <token>'.",
    )

    # Stdio-specific fields
    command = fields.Char(
        string="Command",
        help="Executable to run, e.g. 'npx' or '/usr/local/bin/my-mcp-server'.",
    )
    args = fields.Char(
        string="Arguments",
        help="Space-separated arguments passed to the command, e.g. '-y @upstash/context7-mcp'.",
    )
    env_vars = fields.Text(
        string="Environment Variables",
        help=(
            "Optional KEY=VALUE pairs (one per line) to inject into the process environment.\n"
            "Example:\n  OPENAI_API_KEY=sk-...\n  NODE_ENV=production"
        ),
    )

    # ── Connection ────────────────────────────────────────────────────────────

    timeout = fields.Integer(
        default=DEFAULT_TIMEOUT,
        help="Timeout in seconds for each call.",
    )

    # ── Sync metadata ─────────────────────────────────────────────────────────

    last_sync_date = fields.Datetime(string="Last Synced", readonly=True)
    sync_status = fields.Selection(
        [("never", "Never Synced"), ("ok", "OK"), ("error", "Error")],
        default="never",
        readonly=True,
        tracking=True,
    )
    sync_error = fields.Text(string="Last Sync Error", readonly=True)
    tool_count = fields.Integer(string="Tools", compute="_compute_tool_count")
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

    # ── Constraints ───────────────────────────────────────────────────────────

    @api.constrains("transport", "url", "command")
    def _check_transport_fields(self):
        for rec in self:
            if rec.transport == "http" and not rec.url:
                raise UserError(
                    _("Server '%s': URL is required for HTTP transport.") % rec.name
                )
            if rec.transport == "stdio" and not rec.command:
                raise UserError(
                    _("Server '%s': Command is required for stdio transport.") % rec.name
                )

    # ── JSON-RPC dispatch ─────────────────────────────────────────────────────

    def _jsonrpc_call(self, method, params=None, req_id=1):
        """Dispatch to the correct transport."""
        self.ensure_one()
        if self.transport == "stdio":
            return self._jsonrpc_call_stdio(method, params=params, req_id=req_id)
        return self._jsonrpc_call_http(method, params=params, req_id=req_id)

    def _jsonrpc_session_stdio(self, calls):
        """
        Send multiple JSON-RPC messages in a single stdio process session.

        Args:
            calls: list of (method, params, req_id) tuples to send in order.

        Returns:
            dict mapping req_id -> result for calls that have an id.
            Notifications (no id) are sent but their responses ignored.
        """
        self.ensure_one()
        cmd = [self.command] + (self.args.split() if self.args else [])

        # Build all messages — send as newline-delimited JSON
        messages = []
        ids_with_results = set()
        for method, params, req_id in calls:
            msg = {"jsonrpc": JSONRPC_VERSION, "method": method, "params": params or {}}
            if req_id is not None:
                msg["id"] = req_id
                ids_with_results.add(req_id)
            messages.append(json.dumps(msg))
        payload = "\n".join(messages) + "\n"

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=self._build_stdio_env(),
            )
        except FileNotFoundError:
            raise UserError(
                _("Command not found for '%(name)s': %(cmd)s")
                % {"name": self.name, "cmd": self.command}
            )

        try:
            stdout, stderr = proc.communicate(input=payload, timeout=self.timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            raise UserError(
                _("stdio MCP server '%(name)s' timed out after %(t)d seconds.")
                % {"name": self.name, "t": self.timeout}
            )
        finally:
            try:
                proc.kill()
            except Exception:
                pass

        # Parse all response lines, collect by id
        results = {}
        for line in (stdout or "").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if "id" in data and data["id"] in ids_with_results:
                    results[data["id"]] = self._extract_jsonrpc_result(data)
            except (ValueError, UserError):
                continue

        return results

    # ── HTTP transport ────────────────────────────────────────────────────────

    def _build_headers(self):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
        }
        if self.auth_type == "bearer" and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _jsonrpc_call_http(self, method, params=None, req_id=1):
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
                _("Connection to '%(name)s' timed out after %(t)d seconds.")
                % {"name": self.name, "t": self.timeout}
            )
        except requests.exceptions.ConnectionError as e:
            raise UserError(
                _("Cannot reach '%(name)s': %(err)s") % {"name": self.name, "err": str(e)}
            )
        except requests.exceptions.HTTPError as e:
            raise UserError(
                _("HTTP error from '%(name)s': %(err)s") % {"name": self.name, "err": str(e)}
            )
        try:
            data = resp.json()
        except ValueError:
            raise UserError(
                _("'%(name)s' returned non-JSON: %(body)s")
                % {"name": self.name, "body": resp.text[:200]}
            )
        return self._extract_jsonrpc_result(data)

    # ── Stdio transport ───────────────────────────────────────────────────────

    def _build_stdio_env(self):
        """
        Build the environment dict for the subprocess.
        Starts from the current OS environment so PATH etc. are inherited,
        then overlays any KEY=VALUE pairs from env_vars.
        """
        import os
        env = os.environ.copy()
        if self.env_vars:
            for line in self.env_vars.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
        return env

    def _jsonrpc_call_stdio(self, method, params=None, req_id=1):
        """
        Spawn the stdio MCP server process, send one JSON-RPC request,
        read one JSON-RPC response line, then terminate the process.

        stdio MCP servers are persistent — they don't exit after one message.
        We use Popen (not subprocess.run) so we can:
          1. Write the request to stdin
          2. Read exactly one response line from stdout
          3. Kill the process immediately after

        This avoids blocking the Odoo worker thread indefinitely.
        """
        self.ensure_one()

        cmd = [self.command] + (self.args.split() if self.args else [])
        payload = json.dumps({
            "jsonrpc": JSONRPC_VERSION,
            "id": req_id,
            "method": method,
            "params": params or {},
        }) + "\n"

        _logger.debug("stdio MCP call to %s: %s", self.name, method)

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=self._build_stdio_env(),
            )
        except FileNotFoundError:
            raise UserError(
                _("Command not found for '%(name)s': %(cmd)s\n"
                  "Make sure the executable is installed and on PATH inside the Odoo container.")
                % {"name": self.name, "cmd": self.command}
            )

        try:
            # Write request and read response with timeout
            stdout, stderr = proc.communicate(
                input=payload,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()  # drain to avoid zombie
            raise UserError(
                _("stdio MCP server '%(name)s' did not respond within %(t)d seconds.")
                % {"name": self.name, "t": self.timeout}
            )
        finally:
            # Always clean up the process
            try:
                proc.kill()
            except Exception:
                pass

        stdout = (stdout or "").strip()
        stderr = (stderr or "").strip()

        if not stdout:
            detail = f"\nstderr: {stderr[:500]}" if stderr else ""
            raise UserError(
                _("stdio MCP server '%(name)s' produced no output.%(detail)s")
                % {"name": self.name, "detail": detail}
            )

        # Servers may emit log lines mixed with JSON — find the JSON-RPC response
        data = None
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                candidate = json.loads(line)
                if "jsonrpc" in candidate or "result" in candidate or "error" in candidate:
                    data = candidate
                    break
            except ValueError:
                continue

        if data is None:
            raise UserError(
                _("No valid JSON-RPC response from stdio server '%(name)s'.\n"
                  "Raw output: %(out)s")
                % {"name": self.name, "out": stdout[:300]}
            )

        return self._extract_jsonrpc_result(data)

    def _extract_jsonrpc_result(self, data):
        """Raise UserError on JSON-RPC error, otherwise return result dict."""
        if "error" in data:
            err = data["error"]
            raise UserError(
                _("MCP server '%(name)s' error %(code)s: %(msg)s")
                % {
                    "name": self.name,
                    "code": err.get("code", "?"),
                    "msg": err.get("message", ""),
                }
            )
        return data.get("result", {})

    # ── Public API ────────────────────────────────────────────────────────────

    def action_test_connection(self):
        self.ensure_one()
        try:
            if self.transport == "stdio":
                results = self._jsonrpc_session_stdio([
                    ("initialize", {
                        "protocolVersion": MCP_PROTOCOL_VERSION,
                        "clientInfo": {"name": "Odoo LLM MCP Client", "version": "18.0.1.0.0"},
                        "capabilities": {},
                    }, 1),
                    ("notifications/initialized", {}, None),
                    ("ping", {}, 2),
                ])
                if 1 not in results:
                    raise UserError(_("No response to initialize from '%s'.") % self.name)
            else:
                self._mcp_initialize()
                self._jsonrpc_call("ping", req_id=2)
            self.write({"sync_status": "ok", "sync_error": False})
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
        except Exception as e:
            self.write({"sync_status": "error", "sync_error": str(e)})
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
        self.ensure_one()
        try:
            tools = self._fetch_tools_list()
            stats = self._upsert_tools(tools)
            self.write({
                "last_sync_date": fields.Datetime.now(),
                "sync_status": "ok",
                "sync_error": False,
            })
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Sync Complete"),
                    "message": _(
                        "%(created)d created, %(updated)d updated, %(deactivated)d deactivated."
                    ) % stats,
                    "type": "success",
                    "sticky": False,
                    "next": {"type": "ir.actions.client", "tag": "reload"},
                },
            }
        except Exception as e:
            _logger.exception("MCP tool sync failed for %s", self.name)
            self.write({
                "last_sync_date": fields.Datetime.now(),
                "sync_status": "error",
                "sync_error": str(e),
            })
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
        self.ensure_one()
        try:
            self._jsonrpc_call(
                "initialize",
                params={
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "clientInfo": {"name": "Odoo LLM MCP Client", "version": "18.0.1.0.0"},
                    "capabilities": {},
                },
                req_id=1,
            )
        except UserError as e:
            _logger.debug("MCP initialize failed for %s (may be stateless): %s", self.name, e)

    def _fetch_tools_list(self):
        self.ensure_one()
        if self.transport == "stdio":
            results = self._jsonrpc_session_stdio([
                ("initialize", {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "clientInfo": {"name": "Odoo LLM MCP Client", "version": "18.0.1.0.0"},
                    "capabilities": {},
                }, 1),
                # notifications/initialized has no id (it's a notification)
                ("notifications/initialized", {}, None),
                ("tools/list", {}, 3),
            ])
            result = results.get(3, {})
        else:
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
        self.ensure_one()
        if self.transport == "stdio":
            results = self._jsonrpc_session_stdio([
                ("initialize", {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "clientInfo": {"name": "Odoo LLM MCP Client", "version": "18.0.1.0.0"},
                    "capabilities": {},
                }, 1),
                ("notifications/initialized", {}, None),
                ("tools/call", {"name": tool_name, "arguments": arguments}, 10),
            ])
            result = results.get(10, {})
        else:
            result = self._jsonrpc_call(
                "tools/call",
                params={"name": tool_name, "arguments": arguments},
                req_id=10,
            )
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
        self.ensure_one()
        Tool = self.env["llm.tool"]

        existing = Tool.search(
            [("mcp_server_id", "=", self.id), ("implementation", "=", "mcp_client")]
        )
        existing_by_mcp_name = {t.mcp_tool_name: t for t in existing}

        remote_names = set()
        created = updated = 0

        for tool_def in remote_tools:
            mcp_name = tool_def.get("name", "").strip()
            if not mcp_name:
                continue

            remote_names.add(mcp_name)
            description = tool_def.get("description", "") or ""
            input_schema = tool_def.get("inputSchema") or {}

            # Sanitize: MCP tool names must match ^[a-zA-Z0-9_-]{1,64}$
            safe_server = re.sub(r'[^a-zA-Z0-9_-]', '_', self.name)
            safe_name = f"{safe_server}__{mcp_name}"[:64]

            vals = {
                "name": safe_name,
                "mcp_tool_name": mcp_name,
                "description": description,
                "implementation": "mcp_client",
                "mcp_server_id": self.id,
                "input_schema": json.dumps(input_schema, indent=2) if input_schema else False,
                "active": True,
                "read_only_hint": tool_def.get("annotations", {}).get("readOnlyHint", False),
                "destructive_hint": tool_def.get("annotations", {}).get("destructiveHint", True),
                "idempotent_hint": tool_def.get("annotations", {}).get("idempotentHint", False),
                "open_world_hint": tool_def.get("annotations", {}).get("openWorldHint", True),
            }

            existing_tool = existing_by_mcp_name.get(mcp_name)
            if existing_tool:
                if self._tool_changed(existing_tool, vals):
                    existing_tool.write(vals)
                    updated += 1
            else:
                Tool.create(vals)
                created += 1

        deactivated = 0
        for mcp_name, tool in existing_by_mcp_name.items():
            if mcp_name not in remote_names and tool.active:
                tool.write({"active": False})
                deactivated += 1

        _logger.info(
            "MCP tool sync for '%s': %d created, %d updated, %d deactivated",
            self.name, created, updated, deactivated,
        )
        return {"created": created, "updated": updated, "deactivated": deactivated}

    @staticmethod
    def _tool_changed(tool, vals):
        for f in ("name", "description", "input_schema", "active"):
            if (getattr(tool, f, None) or False) != (vals.get(f) or False):
                return True
        return False
