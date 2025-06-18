import logging

from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class WebhookController(http.Controller):
    
    @http.route('/llm/generate_job/webhook/<int:job_id>', type='json', auth='public', methods=['POST'], csrf=False)
    def generation_job_webhook(self, job_id, **kwargs):
        """Handle webhook notifications from generation providers"""
        try:
            # Get the job record
            job = request.env['llm.generate.job'].sudo().browse(job_id)
            if not job.exists():
                _logger.error(f"Job {job_id} not found for webhook")
                return {"status": "error", "message": "Job not found"}
            
            # Get webhook data
            webhook_data = request.get_json_data()
            if not webhook_data:
                _logger.error(f"No webhook data received for job {job_id}")
                return {"status": "error", "message": "No data received"}
            

            # Process the webhook
            job.process_webhook_result(request,webhook_data)
            
            _logger.info(f"Successfully processed webhook for job {job_id}")
            return {"status": "success"}
            
        except Exception as e:
            _logger.error(f"Error processing webhook for job {job_id}: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}
    
