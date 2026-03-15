"""User Tools - LLM tools for user notifications and interactions"""

import logging

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.llm_tool.decorators import llm_tool

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    """Inherit Users to add LLM tools"""

    _inherit = "res.users"

    @llm_tool(destructive_hint=False, idempotent_hint=False)
    def send_notification_to_user(
        self, user_id: int, title: str, message: str, notification_type: str = "info"
    ) -> dict:
        """Send an in-app notification to a specific user

        Creates a notification that appears in the user's notification center.

        Args:
            user_id: ID of the user to notify
            title: Notification title
            message: Notification message body
            notification_type: Type of notification (info, warning, danger, success)

        Returns:
            Dictionary confirming notification was sent
        """
        # Validate user exists
        user = self.browse(user_id)
        if not user.exists():
            raise UserError(_("User with ID %s not found") % user_id)

        # Validate notification type
        valid_types = ["info", "warning", "danger", "success"]
        if notification_type not in valid_types:
            raise UserError(
                _("Invalid notification_type. Must be one of: %s")
                % ", ".join(valid_types)
            )

        # Send notification via mail.message
        self.env["mail.message"].create(
            {
                "subject": title,
                "body": message,
                "message_type": "notification",
                "partner_ids": [(4, user.partner_id.id)],
                "notification_ids": [
                    (
                        0,
                        0,
                        {
                            "res_partner_id": user.partner_id.id,
                            "notification_type": "inbox",
                        },
                    )
                ],
            }
        )

        return {
            "success": True,
            "user_id": user_id,
            "user_name": user.name,
            "title": title,
            "notification_type": notification_type,
        }

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def get_system_info(self) -> dict:
        """Get basic Odoo system information including version, database name, and module statistics

        This is a utility tool that provides context about the Odoo environment.
        Useful for LLMs to understand the system they're working with.

        Returns:
            Dictionary with system information
        """
        # Get module statistics
        installed_modules = self.env["ir.module.module"].search_count(
            [("state", "=", "installed")]
        )
        total_modules = self.env["ir.module.module"].search_count([])

        # Get user count
        active_users = self.search_count([("active", "=", True)])

        # Get company info
        company = self.env.company

        return {
            "database_name": self.env.cr.dbname,
            "odoo_version": self.env["ir.module.module"]._get_latest_version(),
            "company_name": company.name,
            "company_currency": company.currency_id.name,
            "active_users": active_users,
            "installed_modules": installed_modules,
            "total_modules": total_modules,
        }
