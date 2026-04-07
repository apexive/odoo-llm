import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


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

            # Don't respond to operator messages – only to visitors (partners without users)
            if message.author_id and message.author_id.user_ids:
                return

            self._send_llm_response(channel.id, message.id)

        except Exception as e:
            _logger.error("Error in _maybe_trigger_llm_response: %s", e)

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

            if final_body:
                channel.message_post(
                    body=final_body,
                    message_type="comment",
                    subtype_xmlid="mail.mt_comment",
                )

        except Exception as e:
            _logger.error(
                "Error generating LLM response for channel %s: %s",
                channel_id,
                e,
            )
