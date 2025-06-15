import json
import logging

from odoo import models, api, _
from odoo.exceptions import UserError
import os
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

    def submit_generation_job(self, job_record):
        """Submit a generation job to FAL AI with webhook support"""
        self.ensure_one()
        os.environ.setdefault('FAL_KEY', self.api_key)
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
            """
           arguments={
                "prompt": "Extreme close-up of a single tiger eye, direct frontal view. Detailed iris and pupil. Sharp focus on eye texture and color. Natural lighting to capture authentic eye shine and depth. The word \"FLUX\" is painted over it in big, white brush strokes with visible texture."
            },
            """
            #convertir inputs to a dictionary if it's a string
            if isinstance(inputs, str):
                inputs = json.loads(inputs)
            arguments = {
                "prompt": inputs.get('prompt', ''),
            }

            result = fal_client.submit(
                model_name, 
                arguments=arguments,
                webhook_url=job_record.webhook_url
            )
            
            _logger.info(f"Submitted FAL AI job: {result}")
            
            return {
                'request_id': result.request_id,
                'gateway_request_id': result.request_id,
                'status': 'queued'
            }
            
        except Exception as e:
            import traceback
            _logger.error(f"Error submitting FAL AI generation job: {e}")
            raise UserError(_(f"Failed to submit job to FAL AI: {str(traceback.format_exc())}"))

    def fal_ai_check_generation_job_status(self, job_record):
        """Check the status of a generation job with FAL AI"""
        self.ensure_one()
        os.environ.setdefault('FAL_KEY', self.api_key)
        if not fal_client:
            raise UserError(_("The fal_client package is not installed"))

        if not job_record.external_job_id:
            raise UserError(_("No external job ID found"))

        try:
            # Check status with FAL AI
            status = fal_client.status(
                job_record.model_id.name,
                request_id=job_record.external_job_id,
                with_logs=True
            )

            _logger.info(f"FAL AI job status: {status}")
            class_name = status.__class__.__name__

            # Manejar los diferentes tipos de estado
            if class_name == "Queued":
                # Trabajo en cola
                webhook_data = {
                    'request_id': job_record.external_job_id,
                    'gateway_request_id': job_record.gateway_request_id,
                    'status': 'QUEUED',
                    'position': status.position,
                    'payload': None
                }
                job_record.write({'state': 'queued'})
                return status

            elif class_name == "InProgress":
                # Trabajo en procesamiento
                webhook_data = {
                    'request_id': job_record.external_job_id,
                    'gateway_request_id': job_record.gateway_request_id,
                    'status': 'PROCESSING',
                    'logs': status.logs if hasattr(status, 'logs') and status.logs else [],
                    'payload': None
                }
                job_record.write({'state': 'processing'})
                return status

            elif class_name == "Completed":
                # Trabajo completado, obtener resultado
                result = fal_client.result(
                    job_record.model_id.name,
                    request_id=job_record.external_job_id,
                )

                webhook_data = {
                    'request_id': job_record.external_job_id,
                    'gateway_request_id': job_record.gateway_request_id,
                    'status': 'OK',
                    'logs': status.logs if hasattr(status, 'logs') and status.logs else [],
                    'metrics': status.metrics if hasattr(status, 'metrics') else {},
                    'payload': result
                }
                job_record.process_webhook_result(webhook_data)
                return status

            else:
                # Estado desconocido o error
                _logger.error(f"Tipo de estado desconocido devuelto por FAL AI: {class_name}")
                webhook_data = {
                    'request_id': job_record.external_job_id,
                    'gateway_request_id': job_record.gateway_request_id,
                    'status': 'ERROR',
                    'error': f"Tipo de estado desconocido: {class_name}",
                    'payload': None
                }
                job_record.write({'state': 'error', 'result': json.dumps(webhook_data)})
                return status

        except Exception as e:
            job_record.write({'state': 'failed','error_message': str(e)})
            import traceback
            _logger.error(f"Error al comprobar el estado del trabajo en FAL AI: {traceback.format_exc()}")

    def fal_ai_cancel_generation_job(self, external_job_id):
        """Cancel a generation job with FAL AI"""
        self.ensure_one()
        
        # FAL AI doesn't provide a direct cancel API in the current client
        # This is a placeholder implementation
        _logger.warning(f"FAL AI job cancellation not supported by API. Job ID: {external_job_id}")
        
        # In a real implementation, you would make an API call to cancel the job
        # For now, we just log the attempt
        return {"status": "cancel_not_supported"}
