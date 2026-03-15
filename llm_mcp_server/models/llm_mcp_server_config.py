import re
from urllib.parse import urlparse

from jinja2 import Template
from mcp.types import (
    Implementation,
    InitializeResult,
    ServerCapabilities,
    ToolsCapability,
)

from odoo import api, fields, models
from odoo.exceptions import ValidationError

API_KEY_PLACEHOLDER = "YOUR_API_KEY"

# Claude mcp-remote server config (shared by Claude Desktop and Claude Code)
CLAUDE_SERVER_CONFIG_TEMPLATE = Template("""{
  "type": "stdio",
  "command": "npx",
  "args": [
    "-y",
    "mcp-remote",
    "{{ mcp_url }}",
    "--header",
    "Authorization: Bearer {{ api_key }}"
  ],
  "env": { "MCP_TRANSPORT": "streamable-http" }
}""")

# Configuration Templates by client type
CLIENT_CONFIG_TEMPLATES = {
    "claude_desktop": Template("""{
  "mcpServers": {
    "{{ client_name }}": {{ server_config }}
  }
}"""),
    "claude_code": Template(
        "claude mcp add-json {{ client_name }} '{{ server_config }}'"
    ),
    "codex": Template("""experimental_use_rmcp_client = true

[mcp_servers.{{ client_name }}]
url = "{{ mcp_url }}"
http_headers.Authorization = "Bearer {{ api_key }}"
"""),
}


class LLMMCPServerConfig(models.Model):
    _name = "llm.mcp.server.config"
    _description = "MCP Server Configuration"
    _inherit = ["mail.thread"]

    name = fields.Char(
        string="Server Name",
        required=True,
        default="Odoo LLM MCP Server",
        tracking=True,
    )
    version = fields.Char(
        string="Server Version",
        required=True,
        default="1.0.0",
        tracking=True,
    )
    latest_protocol_version = fields.Char(
        string="Latest Protocol Version",
        required=True,
        help="The latest/default protocol version this server supports",
        tracking=True,
    )
    supported_protocol_versions = fields.Json(
        string="Supported Protocol Versions",
        required=False,
        help="List of additional MCP protocol versions this server supports (excluding latest) in json array[str]",
    )
    all_supported_protocol_versions = fields.Json(
        string="All Supported Protocol Versions",
        compute="_compute_all_supported_protocol_versions",
        help="Complete list of all protocol versions (supported + latest)",
        store=False,
    )
    active = fields.Boolean(
        string="Active",
        default=True,
        tracking=True,
    )
    external_url = fields.Char(
        string="External URL",
        help="External URL that Letta can reach (e.g., http://host.docker.internal:8069 for Docker). "
        "Leave empty to auto-detect from web.base.url",
        tracking=True,
    )
    client_name = fields.Char(
        string="Client Name",
        help="Name used to identify this MCP server in client configurations "
        "(e.g. Claude Desktop, Claude Code, Codex). "
        "Leave empty to auto-generate from the server URL.",
        tracking=True,
    )

    # MCP Server Mode Configuration
    mode = fields.Selection(
        [
            ("stateless", "Stateless Mode"),
            ("stateful", "Stateful Mode"),
        ],
        default="stateful",
        required=True,
        tracking=True,
        help="Server operation mode",
    )

    @api.constrains("active")
    def _check_single_active_record(self):
        """Ensure only one config record can be active at a time"""
        if self.active:
            other_active = self.search([("id", "!=", self.id), ("active", "=", True)])
            if other_active:
                raise ValidationError(
                    "Only one MCP Server configuration can be active at a time."
                )

    @api.model
    def get_active_config(self):
        """Get the active MCP server configuration"""
        config = self.search([("active", "=", True)], limit=1)
        if not config:
            raise ValidationError("No active MCP Server configuration found.")
        return config

    def get_mcp_server_url(self):
        """Get the MCP server URL that external clients can reach"""
        if self.external_url:
            return f"{self.external_url.rstrip('/')}/mcp"
        else:
            base_url = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("web.base.url", "http://localhost:8069")
            )
            return f"{base_url}/mcp"

    def handle_initialize_request(self, client_info=None, protocol_version=None):
        """Handle MCP initialize request - return MCP InitializeResult"""
        server_info = Implementation(name=self.name, version=self.version)

        return InitializeResult(
            protocolVersion=protocol_version,
            capabilities=self._get_server_capabilities(),
            serverInfo=server_info,
        )

    def _get_server_capabilities(self):
        """Get server capabilities based on configuration"""
        capabilities = ServerCapabilities(tools=ToolsCapability(listChanged=False))
        return capabilities

    @api.depends("latest_protocol_version", "supported_protocol_versions")
    def _compute_all_supported_protocol_versions(self):
        """Compute all supported protocol versions (supported + latest)"""
        for record in self:
            all_versions = []
            if record.latest_protocol_version:
                all_versions.append(record.latest_protocol_version)
            if record.supported_protocol_versions:
                all_versions.extend(record.supported_protocol_versions)
            # Remove duplicates while preserving order
            record.all_supported_protocol_versions = list(dict.fromkeys(all_versions))

    def is_protocol_version_supported(self, version):
        """Check if protocol version is supported"""
        if not version:
            return False
        return version in (self.all_supported_protocol_versions or [])

    def get_supported_versions_string(self):
        """Get comma-separated string of supported versions for error messages"""
        if not self.all_supported_protocol_versions:
            return "None configured"
        return ", ".join(self.all_supported_protocol_versions)

    def get_default_protocol_version(self):
        """Get the default protocol version (latest)"""
        return self.latest_protocol_version

    def get_health_status_data(self):
        """Get health status data - return plain dict"""
        return {
            "status": "healthy",
            "server": self.name,
            "version": self.version,
        }

    def action_new_mcp_key(self):
        """Open the MCP key creation wizard."""
        return {
            "type": "ir.actions.act_window",
            "res_model": "res.users.apikeys.description",
            "name": "New MCP Key",
            "views": [(False, "form")],
            "target": "new",
            "context": {
                "is_mcp_key": True,
                "default_name": "MCP Key",
            },
        }

    # Client Configuration Fields (computed with placeholder)
    config_claude_desktop = fields.Text(
        string="Claude Desktop Config",
        compute="_compute_client_configs",
        help="Ready-to-use configuration for Claude Desktop",
    )
    config_claude_code = fields.Text(
        string="Claude Code Config",
        compute="_compute_client_configs",
        help="Ready-to-use command for Claude Code",
    )
    config_codex = fields.Text(
        string="Codex Config",
        compute="_compute_client_configs",
        help="Ready-to-use configuration for Codex CLI",
    )

    @api.depends("external_url", "client_name")
    def _compute_client_configs(self):
        """Compute client configuration snippets with placeholder API key."""
        for record in self:
            configs = record.generate_client_configs()
            record.config_claude_desktop = configs["claude_desktop"]
            record.config_claude_code = configs["claude_code"]
            record.config_codex = configs["codex"]

    def _get_client_name(self):
        """Get the client name for MCP configurations.

        Returns the user-set client_name if present, otherwise
        auto-generates a slug from the hostname and database name.
        """
        self.ensure_one()
        if self.client_name:
            return self.client_name
        mcp_url = self.get_mcp_server_url()
        dbname = self.env.cr.dbname
        return self._slugify_mcp_url(mcp_url, dbname)

    @staticmethod
    def _slugify_mcp_url(url, dbname=""):
        """Generate a slug from the MCP server URL and database name.

        Format: odoo-{hostname}-{dbname}
        Localhost / 127.x addresses are normalized to "localhost".
        """
        parsed = urlparse(url)
        hostname = parsed.hostname or "localhost"

        if hostname in ("localhost", "0.0.0.0") or hostname.startswith("127."):
            hostname = "localhost"

        host_slug = re.sub(r"[^a-z0-9]+", "-", hostname.lower()).strip("-")
        db_slug = re.sub(r"[^a-z0-9]+", "-", dbname.lower()).strip("-") if dbname else ""

        parts = ["odoo", host_slug]
        if db_slug:
            parts.append(db_slug)
        return "-".join(parts)

    def generate_client_configs(self, api_key=None):
        """Generate configuration snippets for each MCP client.

        Args:
            api_key: The API key to use. If None, uses API_KEY_PLACEHOLDER.

        Returns:
            dict with config strings for each client type
        """
        self.ensure_one()
        key = api_key or API_KEY_PLACEHOLDER
        mcp_url = self.get_mcp_server_url()
        client_name = self._get_client_name()

        # Render Claude server config (shared by Claude Desktop and Claude Code)
        server_config = CLAUDE_SERVER_CONFIG_TEMPLATE.render(
            mcp_url=mcp_url, api_key=key
        )

        template_vars = {
            "mcp_url": mcp_url,
            "api_key": key,
            "server_config": server_config,
            "client_name": client_name,
        }

        return {
            client: template.render(**template_vars)
            for client, template in CLIENT_CONFIG_TEMPLATES.items()
        }
