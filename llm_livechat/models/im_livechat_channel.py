import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ImLivechatChannel(models.Model):
    _inherit = "im_livechat.channel"

    llm_assistant_id = fields.Many2one(
        "llm.assistant",
        string="AI Assistant",
        ondelete="set null",
        help="LLM Assistant to automatically respond to visitors",
    )
    llm_auto_reply = fields.Boolean(
        string="Auto Reply",
        default=False,
        help="Enable automatic AI responses to visitor messages",
    )
    llm_delay = fields.Integer(
        string="Response Delay (seconds)",
        default=2,
        help=(
            "Delay before sending automatic response "
            "(to allow human operators to respond first)"
        ),
    )
    llm_greeting_enabled = fields.Boolean(
        string="Send Greeting",
        default=False,
        help="Send an AI-generated greeting when visitor starts chat",
    )

    @api.depends("user_ids.im_status", "llm_auto_reply", "llm_assistant_id")
    def _compute_available_operator_ids(self):
        """Override to make the channel always available when the LLM bot is enabled.

        When llm_auto_reply is True and an assistant is configured, the channel is
        considered available even if no human operators are online, so the live chat
        widget remains visible 24/7.
        """
        super()._compute_available_operator_ids()
        admin_user = self.env.ref("base.user_admin", raise_if_not_found=False)
        for channel in self:
            if (
                channel.llm_auto_reply
                and channel.llm_assistant_id
                and not channel.available_operator_ids
            ):
                # No human operators online – fall back to the channel's own
                # members (bot users) so the correct name is displayed in the
                # widget instead of the currently logged-in user.
                if channel.user_ids:
                    channel.available_operator_ids = channel.user_ids[:1]
                # No human operators online – fall back to admin as a virtual
                # placeholder so the channel is treated as available.
                if admin_user:
                    channel.available_operator_ids = admin_user
