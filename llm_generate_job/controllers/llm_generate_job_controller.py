import json
import logging

from odoo import http
from odoo.addons.llm_mail_message_subtypes.const import (
    LLM_TOOL_RESULT_SUBTYPE_XMLID,
    LLM_USER_SUBTYPE_XMLID,
)
from odoo.addons.llm_thread.controllers.llm_thread import LLMThreadController
from odoo.http import Response, request

_logger = logging.getLogger(__name__)


class LLMGenerateJobThreadController(LLMThreadController):

    @http.route("/llm/thread/generate-media-async", type="http", auth="user", csrf=True)
    def llm_thread_generate_media_async(
            self, thread_id, message=None, generation_inputs=None, **kwargs
    ):
        """Generate media using async job queue with webhook support"""
        try:
            # Parse inputs
            if isinstance(generation_inputs, str):
                generation_inputs = json.loads(generation_inputs)

            # Get thread
            thread = request.env["llm.thread"].browse(int(thread_id))
            if not thread.exists():
                return Response(
                    json.dumps({"error": "Thread not found"}),
                    content_type="application/json",
                    status=404
                )

            # Check if provider supports async generation
            if not hasattr(thread.provider_id, 'fal_ai_supports_async_generation') or \
                    not thread.provider_id.fal_ai_supports_async_generation():
                # Fall back to synchronous generation
                return self.llm_thread_generate_media(
                    thread_id, message, json.dumps(generation_inputs) if generation_inputs else None, **kwargs
                )

            # Process inputs with prompt if needed
            processed_inputs = request.env["llm.thread"].process_prompt_for_media_gen(
                thread_id, json.dumps(generation_inputs) if generation_inputs else "{}"
            )

            # Create generation job
            job_vals = {
                'name': f"Media Generation - {thread.name}",
                'provider_id': thread.provider_id.id,
                'model_id': thread.model_id.id,
                'thread_id': thread.id,
                'generation_inputs': processed_inputs,
            }

            job = request.env['llm.generate.job'].create(job_vals)

            # Submit job
            job.action_submit()

            # Return immediate response with job ID
            response_data = {
                "job_id": job.id,
                "status": "submitted",
                "message": "Generation job submitted successfully. You will be notified when complete."
            }

            # Post initial message to thread
            thread.message_post(
                body=f"🚀 **Generation job submitted**\n\nJob ID: {job.id}\nStatus: {job.state}\n\nYou will be notified when the generation is complete.",
                subtype_xmlid='llm_mail_message_subtypes.llm_assistant'
            )

            return Response(
                json.dumps(response_data),
                content_type="application/json"
            )

        except Exception as e:
            _logger.error(f"Error in async media generation: {e}", exc_info=True)
            return Response(
                json.dumps({"error": str(e)}),
                content_type="application/json",
                status=500
            )

    @http.route("/llm/generate_job/<int:job_id>/status", type="json", auth="user", methods=["GET"])
    def get_job_status(self, job_id):
        """Get the status of a generation job"""
        try:
            job = request.env['llm.generate.job'].browse(job_id)
            if not job.exists():
                return {"error": "Job not found"}

            # Check if user has access to this job
            if job.create_uid.id != request.env.user.id and not request.env.user.has_group(
                    'llm_generate_job.group_llm_generation_job_manager'):
                return {"error": "Access denied"}

            return {
                "job_id": job.id,
                "name": job.name,
                "state": job.state,
                "submitted_date": job.submitted_date.isoformat() if job.submitted_date else None,
                "completed_date": job.completed_date.isoformat() if job.completed_date else None,
                "error_message": job.error_message,
                "retry_count": job.retry_count,
                "max_retries": job.max_retries,
                "external_job_id": job.external_job_id,
            }

        except Exception as e:
            _logger.error(f"Error getting job status: {e}")
            return {"error": str(e)}

    @http.route("/llm/generate_job/<int:job_id>/cancel", type="json", auth="user", methods=["POST"])
    def cancel_job(self, job_id):
        """Cancel a generation job"""
        try:
            job = request.env['llm.generate.job'].browse(job_id)
            if not job.exists():
                return {"error": "Job not found"}

            # Check if user has access to this job
            if job.create_uid.id != request.env.user.id and not request.env.user.has_group(
                    'llm_generate_job.group_llm_generation_job_manager'):
                return {"error": "Access denied"}

            job.action_cancel()

            return {
                "job_id": job.id,
                "state": job.state,
                "message": "Job cancelled successfully"
            }

        except Exception as e:
            _logger.error(f"Error cancelling job: {e}")
            return {"error": str(e)}

    @http.route("/llm/generate_job/<int:job_id>/retry", type="json", auth="user", methods=["POST"])
    def retry_job(self, job_id):
        """Retry a failed generation job"""
        try:
            job = request.env['llm.generate.job'].browse(job_id)
            if not job.exists():
                return {"error": "Job not found"}

            # Check if user has access to this job
            if job.create_uid.id != request.env.user.id and not request.env.user.has_group(
                    'llm_generate_job.group_llm_generation_job_manager'):
                return {"error": "Access denied"}

            job.action_retry()

            return {
                "job_id": job.id,
                "state": job.state,
                "retry_count": job.retry_count,
                "message": "Job retried successfully"
            }

        except Exception as e:
            _logger.error(f"Error retrying job: {e}")
            return {"error": str(e)}

    @http.route("/api/llm/provider/supports_async_generation", type="json", auth="user", methods=["GET", "POST"])
    def check_async_generation_support(self, provider_id=None, thread_id=None, **kwargs):
        """Check if a provider supports async generation"""
        try:
            provider = None

            # Primero intentamos obtener el provider desde el thread_id
            if thread_id:
                thread = request.env["llm.thread"].browse(int(thread_id))
                if not thread.exists():
                    return {"error": "Thread not found", "supports_async": False}

                # Obtener el provider desde el thread
                provider = thread.provider_id

                if not provider:
                    return {"error": "No provider found for this thread", "supports_async": False}

            # Si no hay thread_id pero hay provider_id, usar el provider directamente
            elif provider_id:
                provider = request.env["llm.provider"].browse(int(provider_id))
                if not provider.exists():
                    return {"error": "Provider not found", "supports_async": False}

            # Si no se proporciona ni thread_id ni provider_id, error
            else:
                return {"error": "Either thread_id or provider_id is required", "supports_async": False}

            # Verificar si el provider soporta generación asíncrona
            supports_async = False
            if hasattr(provider, 'supports_async_generation'):
                supports_async = provider.supports_async_generation()

            return {
                "supports_async": supports_async,
                "provider_name": provider.name,
                "provider_id": provider.id
            }

        except Exception as e:
            _logger.error(f"Error checking async generation support: {e}")
            return {"error": str(e), "supports_async": False}

    @http.route("/api/llm/thread/submit_async_generation", type="json", auth="user", methods=["POST"])
    def submit_async_generation(self, thread_id=None, generation_inputs=None, model_id=None, **kwargs):
        """Submit an async generation job"""
        try:
            if not thread_id:
                return {"error": "thread_id is required", "success": False}

            # Get thread
            thread = request.env["llm.thread"].browse(int(thread_id))
            if not thread.exists():
                return {"error": "Thread not found", "success": False}

            # Publicar el mensaje del usuario antes de procesar
            prompt = generation_inputs.get('prompt', '') if isinstance(generation_inputs, dict) else ''
            if prompt:
                thread._post_message(
                    body=prompt,
                    subtype_xmlid=LLM_USER_SUBTYPE_XMLID,
                    author_id=request.env.user.partner_id.id
                )

            # Procesar el prompt para la generación de medios
            generation_inputs = request.env["llm.thread"].process_prompt_for_media_gen(
                thread_id, generation_inputs
            )

            # Create generation job
            job_vals = {
                'name': f"Media Generation - {thread.name}",
                'provider_id': thread.provider_id.id,
                'model_id': model_id or thread.model_id.id,
                'thread_id': thread.id,
                'state': 'draft',
                'generation_inputs': json.dumps(generation_inputs) if generation_inputs else "{}",
            }

            job = request.env['llm.generate.job'].sudo().create(job_vals)

            # Submit the job
            job.action_submit()

            # Notificación de trabajo enviado
            thread._post_message(
                body="🚀 **Generation job submitted**\n You will be notified when the generation is complete.",
                subtype_xmlid=LLM_TOOL_RESULT_SUBTYPE_XMLID,
                tool_name = "llm_generate_job",
                tool_call_result =json.dumps(
                    {"message": f"Job ID: {job.id} Status: {job.state}"
                    }
                )
            )

            return {
                "success": True,
                "job_id": job.id,
                "job_name": job.name,
                "state": job.state,
                "message": "Generation job submitted successfully"
            }

        except Exception as e:
            _logger.error(f"Error submitting async generation job: {e}")
            return {"error": str(e), "success": False}
