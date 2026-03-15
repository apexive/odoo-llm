import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class WebhookController(http.Controller):
    @http.route(
        "/llm/generate_job/webhook/<int:job_id>",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def generation_job_webhook(self, job_id, **kwargs):
        """Handle webhook notifications from FAL.AI for generation jobs"""
        try:
            # Get the job record with sudo for public access
            job = request.env["llm.generation.job"].sudo().browse(job_id)
            if not job.exists():
                _logger.error(f"Job {job_id} not found for webhook")
                return {"status": "error", "message": "Job not found"}

            # Get webhook data
            webhook_data = request.get_json_data()
            if not webhook_data:
                _logger.error(f"No webhook data received for job {job_id}")
                return {"status": "error", "message": "No data received"}

            # Get the provider and process the webhook
            provider = job.provider_id.sudo()
            if hasattr(provider, "process_webhook_result"):
                provider.process_webhook_result(webhook_data, job)
            else:
                _logger.error(
                    f"Provider {provider.service} does not support webhook processing"
                )
                return {
                    "status": "error",
                    "message": "Provider does not support webhooks",
                }

            _logger.info(f"Successfully processed webhook for job {job_id}")
            return {"status": "success"}

        except Exception as e:
            _logger.error(
                f"Error processing webhook for job {job_id}: {e}", exc_info=True
            )
            return {"status": "error", "message": str(e)}
