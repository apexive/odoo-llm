import json
import logging

from odoo import http
from odoo.http import Response, request

from odoo.addons.llm_thread.controllers.llm_thread import LLMThreadController

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
            if job.create_uid.id != request.env.user.id and not request.env.user.has_group('llm_generate_job.group_llm_generation_job_manager'):
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
            if job.create_uid.id != request.env.user.id and not request.env.user.has_group('llm_generate_job.group_llm_generation_job_manager'):
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
            if job.create_uid.id != request.env.user.id and not request.env.user.has_group('llm_generate_job.group_llm_generation_job_manager'):
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
    def check_async_generation_support(self, provider_id=None, **kwargs):
        """Check if a provider supports async generation"""
        try:
            if not provider_id:
                return {"error": "provider_id is required", "supports_async": False}
            
            provider = request.env["llm.provider"].browse(int(provider_id))
            if not provider.exists():
                return {"error": "Provider not found", "supports_async": False}
            
            # Check if provider supports async generation
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
            
            # Check if provider supports async generation
            #TODO: Uncomment the following lines when the provider supports async generation check
            # if not hasattr(thread.provider_id, 'supports_async_generation') or \
            #    not thread.provider_id.supports_async_generation():
            #     return {"error": "Provider does not support async generation", "success": False}
            
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
