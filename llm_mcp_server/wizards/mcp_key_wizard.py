from odoo import _, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.base.models.res_users import check_identity


class APIKeyDescriptionMCP(models.TransientModel):
    """Extend API Key Description wizard to support MCP key generation."""

    _inherit = "res.users.apikeys.description"

    @check_identity
    def make_key(self):
        """Override to show MCP configs when is_mcp_key context is set."""
        if not self.env.context.get("is_mcp_key"):
            return super().make_key()

        # Same key generation logic as parent
        self.check_access_make_key()

        description = self.sudo()
        k = self.env["res.users.apikeys"]._generate(
            None, description.name, self.expiration_date
        )
        description.unlink()

        # Get MCP config and generate client configs with actual API key
        try:
            config = self.env["llm.mcp.server.config"].get_active_config()
        except ValidationError:
            # No active MCP config, create temporary one for URL generation
            config = self.env["llm.mcp.server.config"].new({})

        mcp_url = config.get_mcp_server_url()
        configs = config.generate_client_configs(api_key=k)

        # Return MCP-specific show view with configs
        return {
            "type": "ir.actions.act_window",
            "res_model": "llm.mcp.key.show",
            "name": _("MCP Key Ready"),
            "views": [(False, "form")],
            "target": "new",
            "context": {
                "default_key": k,
                "default_mcp_url": mcp_url,
                "default_config_claude_desktop": configs["claude_desktop"],
                "default_config_claude_code": configs["claude_code"],
                "default_config_codex": configs["codex"],
            },
        }


class LlmMcpKeyShow(models.AbstractModel):
    """Show MCP Key with ready-to-use configuration snippets."""

    _name = "llm.mcp.key.show"
    _description = "Show MCP Key with Configs"

    # Required for onchange that returns the key value
    id = fields.Id()
    key = fields.Char(readonly=True)
    mcp_url = fields.Char(readonly=True, string="MCP URL")

    # Config snippets for different clients (populated via context defaults)
    config_claude_desktop = fields.Text(readonly=True, string="Claude Desktop")
    config_claude_code = fields.Text(readonly=True, string="Claude Code")
    config_codex = fields.Text(readonly=True, string="Codex (OpenAI)")
