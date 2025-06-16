import json
import logging

from odoo import _, api, models
from odoo.addons.llm_mail_message_subtypes.const import (
    LLM_ASSISTANT_SUBTYPE_XMLID,
)
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class LLMThread(models.Model):
    _inherit = "llm.thread"

    def _next_step(self, last_message):
        """Dispatch to the next generator based on message type."""
        if last_message.is_llm_user_media_gen_message():
            return self._get_media_gen_response(last_message)
        return super()._next_step(last_message)

    def _get_media_gen_response(self, user_message):
        self.ensure_one()

        generation_inputs = user_message.generation_inputs
        user_message_body = user_message.body
        stream_response = self.model_id.generate_media(
            json.loads(generation_inputs), stream=True
        )

        assistant_msg = yield from self.env[
            "mail.message"
        ].create_message_from_media_gen_stream(
            self,
            stream_response,
            LLM_ASSISTANT_SUBTYPE_XMLID,
            placeholder_text=f'<em>"{user_message_body}"</em>',
        )
        return assistant_msg

    @api.model
    def build_update_vals(
            self,
            subtype_xmlid,
            tool_call_id=None,
            tool_calls=None,
            tool_call_definition=None,
            tool_call_result=None,
            **kwargs,
    ):
        base_vals = super().build_update_vals(
            subtype_xmlid,
            tool_call_id=tool_call_id,
            tool_calls=tool_calls,
            tool_call_definition=tool_call_definition,
            tool_call_result=tool_call_result,
        )
        if base_vals:
            return base_vals
        generation_inputs = kwargs.get("generation_inputs")
        attachment_ids = kwargs.get("attachment_ids")
        vals = {
            "generation_inputs": generation_inputs,
            "attachment_ids": attachment_ids,
        }
        return {k: v for k, v in vals.items() if v is not None}

    @api.model
    def process_prompt_for_media_gen(self, thread_id, generation_inputs):
        if isinstance(thread_id, str):
            thread_id = int(thread_id)
        thread = self.browse(thread_id)
        if not thread or not thread.assistant_id or not thread.assistant_id.prompt_id:
            return generation_inputs

        # Create a context with the thread_id
        context = dict(self.env.context, thread_id=thread.id)
        # Use the prompt with the new context
        result = thread.with_context(
            context
        ).assistant_id.prompt_id.get_formatted_system_prompt(generation_inputs)
        try:
            result = json.loads(result)
            return json.dumps(result)
        except Exception as e:
            _logger.error("Invalid JSON in prompt result: %s", str(e))
            raise UserError(
                _("The prompt template produced invalid JSON: %s") % str(e)
            ) from e
