import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    llm_thread_id = fields.Many2one(
        "llm.thread",
        string="LLM Thread",
        ondelete="set null",
        help="Associated LLM thread for AI conversations",
        copy=False,
    )

    def _get_or_create_llm_thread(self):
        """Get or create LLM thread for this channel."""
        self.ensure_one()

        if (
            not self.livechat_channel_id
            or not self.livechat_channel_id.llm_assistant_id
        ):
            return None

        if self.llm_thread_id:
            return self.llm_thread_id

        assistant = self.livechat_channel_id.llm_assistant_id
        thread = self.env["llm.thread"].create(
            {
                "name": f"Live Chat - {self.name}",
                "model": self._name,
                "res_id": self.id,
                "assistant_id": assistant.id,
                "provider_id": assistant.provider_id.id,
                "model_id": assistant.model_id.id,
            }
        )
        self.llm_thread_id = thread.id
        return thread

    def _send_llm_greeting(self):
        """Send AI greeting message when chat starts."""
        self.ensure_one()

        if (
            not self.livechat_channel_id
            or not self.livechat_channel_id.llm_greeting_enabled
        ):
            return

        thread = self._get_or_create_llm_thread()
        if not thread:
            return

        try:
            greeting_prompt = "Greet the visitor and ask how you can help them."
            llm_message = thread.message_post(
                body=greeting_prompt,
                llm_role="user",
                author_id=self.env.user.partner_id.id,
            )

            final_body = None
            for event in thread.generate_messages(llm_message):
                if event.get("type") == "message_update":
                    body = event.get("message", {}).get("body")
                    if body and body.strip():
                        final_body = body

            if final_body:
                self.message_post(
                    body=final_body,
                    message_type="comment",
                    subtype_xmlid="mail.mt_comment",
                )

        except Exception as e:
            _logger.error(
                "Error sending LLM greeting to channel %s: %s",
                self.id,
                e,
            )
