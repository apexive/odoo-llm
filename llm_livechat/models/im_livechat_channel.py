import logging

from odoo import fields, models

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
