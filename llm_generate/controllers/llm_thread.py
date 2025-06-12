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

    @http.route("/api/llm/provider/supports_async_generation", type="json", auth="user", csrf=True)
    def check_async_generation_support(self, provider_id, **kwargs):
        """Check if a provider supports async generation"""
        try:
            provider = request.env["llm.provider"].browse(int(provider_id))
            if not provider.exists():
                return {"supports_async": False, "error": "Provider not found"}

            supports_async = provider.supports_async_generation()
            return {"supports_async": supports_async}

        except Exception as e:
            _logger.exception("Error checking async generation support")
            return {"supports_async": False, "error": str(e)}

    @http.route("/api/llm/thread/submit_async_generation", type="json", auth="user", csrf=True)
    def submit_async_generation(self, thread_id, generation_inputs, model_id=None, **kwargs):
        """Submit an async generation job"""
        try:
            thread = request.env["llm.thread"].browse(int(thread_id))
            if not thread.exists():
                return {"success": False, "error": "Thread not found"}

            # Set model_id if provided
            if model_id:
                thread = thread.with_context(force_model_id=int(model_id))

            # Process generation inputs through prompt if needed
            processed_inputs = request.env["llm.thread"].process_prompt_for_media_gen(
                thread_id, generation_inputs
            )

            # Parse back to dict if it was stringified
            if isinstance(processed_inputs, str):
                processed_inputs = json.loads(processed_inputs)

            # Submit async generation job
            job = thread.submit_async_generation(processed_inputs, auto_submit=True)

            return {
                "success": True,
                "job_id": job.id,
                "job_state": job.state,
                "message": f"Generation job {job.id} submitted successfully"
            }

        except Exception as e:
            _logger.exception("Error submitting async generation job")
            return {
                "success": False,
                "error": str(e)
            }
