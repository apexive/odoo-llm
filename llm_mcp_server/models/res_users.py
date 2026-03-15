from odoo import _, models


class ResUsers(models.Model):
    """Extend res.users to add MCP key generation action."""

    _inherit = "res.users"

    def action_new_mcp_key(self):
        """Open standard API key wizard with MCP context.

        This triggers the same wizard as 'New API Key' but with context
        that redirects to the MCP config show view after key generation.
        """
        return {
            "type": "ir.actions.act_window",
            "res_model": "res.users.apikeys.description",
            "name": _("New MCP Key"),
            "views": [(False, "form")],
            "target": "new",
            "context": {
                "is_mcp_key": True,
                "default_name": "MCP Key",
            },
        }
