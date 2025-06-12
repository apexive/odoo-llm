import json
import logging

from odoo import models, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import fal_client
except ImportError:
    _logger.warning("Could not import fal_client. Install the package with pip: pip install fal_client")
    fal_client = None


class LLMProvider(models.Model):
    _inherit = "llm.provider"

    def fal_ai_supports_async_generation(self):
        """FAL AI supports async generation with webhooks"""
        return True

    def fal_ai_submit_generation_job(self, job_record):
        """Submit a generation job to FAL AI with webhook support"""
        self.ensure_one()
        
        if not fal_client:
            raise UserError(_("The fal_client package is not installed. Install it with pip: pip install fal_client"))
        
        # Get the model name
        model_name = job_record.model_id.name
        if not model_name:
            raise UserError(_("Model name is required"))
        
        # Prepare inputs
        inputs = job_record.generation_inputs
        if not inputs:
            raise UserError(_("Generation inputs are required"))
        
        try:
            # Submit to FAL AI queue with webhook
            # FAL AI uses queue.submit for async operations
            result = fal_client.queue.submit(
                model_name, 
                input=inputs,
                webhookUrl=job_record.webhook_url
            )
            
            _logger.info(f"Submitted FAL AI job: {result}")
            
            return {
                'request_id': result.get('request_id'),
                'gateway_request_id': result.get('request_id'),  # FAL uses same ID
                'status': 'queued'
            }
            
        except Exception as e:
            _logger.error(f"Error submitting FAL AI generation job: {e}")
            raise UserError(_(f"Failed to submit job to FAL AI: {str(e)}"))

    def fal_ai_check_generation_job_status(self, job_record):
        """Check the status of a generation job with FAL AI"""
        self.ensure_one()
        
        if not fal_client:
            raise UserError(_("The fal_client package is not installed"))
        
        if not job_record.external_job_id:
            raise UserError(_("No external job ID found"))
        
        try:
            # Check status with FAL AI
            status = fal_client.queue.status(
                job_record.model_id.name,
                requestId=job_record.external_job_id,
                logs=True
            )
            
            _logger.info(f"FAL AI job status: {status}")
            
            # Update job based on status
            if status.get('status') == 'completed':
                # Get the result
                result = fal_client.queue.result(
                    job_record.model_id.name,
                    requestId=job_record.external_job_id
                )
                
                # Simulate webhook data format
                webhook_data = {
                    'request_id': job_record.external_job_id,
                    'gateway_request_id': job_record.gateway_request_id,
                    'status': 'OK',
                    'payload': result.data
                }
                
                job_record.process_webhook_result(webhook_data)
                
            elif status.get('status') == 'failed':
                # Handle failed job
                webhook_data = {
                    'request_id': job_record.external_job_id,
                    'gateway_request_id': job_record.gateway_request_id,
                    'status': 'ERROR',
                    'error': status.get('error', 'Job failed'),
                    'payload': None
                }
                
                job_record.process_webhook_result(webhook_data)
                
            elif status.get('status') in ['queued', 'processing']:
                # Update job state if needed
                if job_record.state == 'submitted' and status.get('status') == 'processing':
                    job_record.write({
                        'state': 'processing',
                        'started_date': job_record.env.cr.now()
                    })
            
            return status
            
        except Exception as e:
            _logger.error(f"Error checking FAL AI job status: {e}")
            raise UserError(_(f"Failed to check FAL AI job status: {str(e)}"))

    def fal_ai_cancel_generation_job(self, external_job_id):
        """Cancel a generation job with FAL AI"""
        self.ensure_one()
        
        # FAL AI doesn't provide a direct cancel API in the current client
        # This is a placeholder implementation
        _logger.warning(f"FAL AI job cancellation not supported by API. Job ID: {external_job_id}")
        
        # In a real implementation, you would make an API call to cancel the job
        # For now, we just log the attempt
        return {"status": "cancel_not_supported"}
