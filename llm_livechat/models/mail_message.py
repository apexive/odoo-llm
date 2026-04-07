import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


# Simple emoji code to Unicode mapping
EMOJI_MAP = {
    ":wave:": "👋",
    ":waving_hand:": "👋",
    ":hand:": "👋",
    ":rocket:": "🚀",
    ":wrench:": "🔧",
    ":hammer:": "🔨",
    ":gear:": "⚙️",
    ":bulb:": "💡",
    ":light_bulb:": "💡",
    ":fire:": "🔥",
    ":zap:": "⚡",
    ":high_voltage:": "⚡",
    ":star:": "⭐",
    ":sparkles:": "✨",
    ":tada:": "🎉",
    ":party:": "🎉",
    ":checkmark:": "✅",
    ":white_check_mark:": "✅",
    ":check:": "✅",
    ":x:": "❌",
    ":cross_mark:": "❌",
    ":warning:": "⚠️",
    ":bell:": "🔔",
    ":loudspeaker:": "📢",
    ":eyes:": "👀",
    ":brain:": "🧠",
    ":heart:": "❤️",
    ":thumbsup:": "👍",
    ":thumbs_up:": "👍",
    ":+1:": "👍",
    ":thumbsdown:": "👎",
    ":thumbs_down:": "👎",
    ":-1:": "👎",
    ":raised_hands:": "🙌",
    ":clap:": "👏",
    ":smile:": "😊",
    ":smiley:": "😊",
    ":grinning:": "😀",
    ":wink:": "😉",
    ":thinking:": "🤔",
    ":books:": "📚",
    ":book:": "📖",
    ":memo:": "📝",
    ":pencil:": "✏️",
    ":clipboard:": "📋",
    ":calendar:": "📅",
    ":package:": "📦",
    ":inbox_tray:": "📥",
    ":outbox_tray:": "📤",
    ":link:": "🔗",
    ":email:": "📧",
    ":envelope:": "✉️",
    ":phone:": "📞",
    ":telephone_receiver:": "📞",
    ":mobile_phone:": "📱",
    ":iphone:": "📱",
    ":bar_chart:": "📊",
    ":chart_increasing:": "📈",
    ":chart_with_upwards_trend:": "📈",
    ":mag:": "🔍",
    ":mag_right:": "🔎",
    ":key:": "🔑",
    ":lock:": "🔒",
    ":locked:": "🔒",
    ":unlock:": "🔓",
    ":shield:": "🛡️",
    ":robot:": "🤖",
    ":telescope:": "🔭",
    ":dollar:": "💰",
    ":moneybag:": "💵",
    ":stopwatch:": "⏱️",
    ":alarm_clock:": "⏰",
    ":hourglass:": "⏳",
    ":dart:": "🎯",
    ":bullseye:": "🎯",
    ":trophy:": "🏆",
    ":office:": "🏢",
    ":office_building:": "🏢",
    ":house:": "🏠",
    ":test_tube:": "🧪",
    ":microscope:": "🔬",
    ':flexed_biceps:': '💪',
    ':muscle:': '💪',
    ':handshake:': '🤝',
    ':money_bag:': '💰',
    ':smilingfacewithsmilingeyes:': '😊',
}


def _convert_emoji_codes(text):
    """Convert :emoji_code: to Unicode emojis.

    This is a simple, safe conversion that doesn't touch HTML or Markdown.
    """
    if not text:
        return text

    for code, emoji in EMOJI_MAP.items():
        text = text.replace(code, emoji)

    return text


class MailMessage(models.Model):
    _inherit = "mail.message"

    @api.model_create_multi
    def create(self, vals_list):
        """Intercept live chat messages to trigger LLM assistant."""
        messages = super().create(vals_list)

        for message in messages:
            if message.model == "discuss.channel" and message.message_type == "comment":
                self._maybe_trigger_llm_response(message)

        return messages

    def _maybe_trigger_llm_response(self, message):
        """Check if we should trigger LLM response for this message."""

        # CRITICAL: Skip if this message was posted by the LLM system itself
        if self.env.context.get("llm_response"):
            return

        try:
            channel = self.env["discuss.channel"].browse(message.res_id)

            if not channel.livechat_channel_id:
                return

            livechat_config = channel.livechat_channel_id
            if (
                not livechat_config.llm_auto_reply
                or not livechat_config.llm_assistant_id
            ):
                return

            # Don't respond to the bot's own messages (OdooBot / admin)
            bot_partner = self.env.ref("base.partner_root", raise_if_not_found=False)
            if bot_partner and message.author_id == bot_partner:
                return

            # Don't respond to operator messages – only to visitors
            if message.author_id and message.author_id.user_ids:
                return

            # Rate limiting protection
            last_messages = self.env["mail.message"].search(
                [
                    ("model", "=", "discuss.channel"),
                    ("res_id", "=", channel.id),
                    ("create_date", ">", fields.Datetime.now() - timedelta(seconds=5)),
                ],
                order="create_date DESC",
                limit=5,
            )

            visitor_count = sum(
                1
                for msg in last_messages
                if msg.author_id and not msg.author_id.user_ids
            )

            if visitor_count > 2:
                _logger.warning(
                    "Rate limit: Too many visitor messages in channel %s",
                    channel.id,
                )
                return

            self._send_llm_response(channel.id, message.id)

        except Exception as e:
            _logger.exception("Error in _maybe_trigger_llm_response: %s", e)

    @api.model
    def _send_llm_response(self, channel_id, user_message_id):
        """Generate and send LLM response to live chat channel."""
        try:
            channel = self.env["discuss.channel"].browse(channel_id)
            user_message = self.env["mail.message"].browse(user_message_id)

            if not channel.exists() or not user_message.exists():
                return

            thread = channel._get_or_create_llm_thread()
            if not thread:
                return

            llm_message = thread.message_post(
                body=user_message.body,
                llm_role="user",
                author_id=user_message.author_id.id,
            )

            final_body = None
            for event in thread.generate_messages(llm_message):
                if event.get("type") == "message_update":
                    body = event.get("message", {}).get("body")
                    if body and body.strip():
                        final_body = body

            # Post the final response to live chat (with protection against re-triggering)
            if final_body:
                # Simple emoji conversion only
                formatted_body = _convert_emoji_codes(final_body)

                # Use context to prevent re-triggering
                channel.with_context(llm_response=True).message_post(
                    body=formatted_body,
                    message_type="comment",
                    subtype_xmlid="mail.mt_comment",
                )
                _logger.info("LLM response posted to channel %s", channel_id)

        except Exception as e:
            _logger.error(
                "Error generating LLM response for channel %s: %s",
                channel_id,
                e,
            )
