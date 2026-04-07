import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def _cron_keep_bot_operators_online(self):
        """Cron job to keep bot operators online.

        This ensures that users who are members of live chat channels with
        AI auto-reply enabled always appear as "online" to website visitors.

        Runs every 15 minutes to update their last activity time.
        """
        # Find all live chat channels with AI auto-reply enabled
        channels = self.env["im_livechat.channel"].search(
            [
                ("llm_auto_reply", "=", True),
                ("llm_assistant_id", "!=", False),
            ]
        )

        if not channels:
            _logger.debug("No live chat channels with AI auto-reply found")
            return

        # Collect all unique users from these channels
        bot_users = self.env["res.users"]
        for channel in channels:
            bot_users |= channel.user_ids

        if not bot_users:
            _logger.warning(
                "Channels with AI auto-reply have no members: %s",
                channels.mapped("name"),
            )
            return

        # Update their last activity to keep them "online"
        now = fields.Datetime.now()

        # Flush pending ORM writes before direct SQL to avoid data inconsistency
        self.env.flush_all()

        # Use SQL for efficiency (avoid ORM overhead and write checks)
        self.env.cr.execute(
            """
            UPDATE res_users
            SET last_activity = %s
            WHERE id IN %s
            """,
            (now, tuple(bot_users.ids)),
        )

        _logger.info(
            "Kept %d bot operators online for channels: %s",
            len(bot_users),
            ", ".join(channels.mapped("name")),
        )
