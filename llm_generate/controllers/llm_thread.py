import json
import logging

from odoo import http
from odoo.http import Response, request

from odoo.addons.llm_thread.controllers.llm_thread import LLMThreadController

_logger = logging.getLogger(__name__)


class LLMThreadControllerExtended(LLMThreadController):
    @http.route("/llm/thread/generate-media", type="http", auth="user", csrf=True)
    def llm_thread_generate_media(
        self, thread_id, message=None, generation_inputs=None, **kwargs
    ):
        headers = {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
        user_message_body = message
        generation_inputs = request.env["llm.thread"].process_prompt_for_media_gen(
            thread_id, generation_inputs
        )
        return Response(
            self._llm_thread_generate(
                request.cr.dbname,
                request.env,
                thread_id,
                user_message_body,
                generation_inputs=generation_inputs,
            ),
            direct_passthrough=True,
            headers=headers,
        )
