import json
import logging
from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

from odoo.addons.llm_mail_message_subtypes.const import (
    LLM_USER_SUBTYPE_XMLID,
)

_logger = logging.getLogger(__name__)


class LLMGenerateJob(models.Model):
    _name = "llm.generate.job"
    _description = "LLM Generation Job"
    _inherit = ["mail.thread"]
    _order = "create_date DESC"

    name = fields.Char(required=True, tracking=True)
    description = fields.Text(tracking=True)
    active = fields.Boolean(default=True)

    # Provider and model information
    provider_id = fields.Many2one(
        "llm.provider", 
        string="LLM Provider", 
        required=True, 
        tracking=True
    )
    model_id = fields.Many2one(
        "llm.model",
        string="Model",
        required=True,
        domain="[('provider_id', '=', provider_id)]",
        tracking=True,
    )

    # Thread relationship
    thread_id = fields.Many2one(
        "llm.thread",
        string="Thread",
        required=True,
        ondelete="cascade",
        tracking=True,
        help="The thread where results will be posted"
    )

    # Job configuration
    generation_inputs = fields.Json(
        string="Generation Inputs",
        required=True,
        help="JSON data containing the generation parameters"
    )
    
    webhook_url = fields.Char(
        string="Webhook URL",
        help="URL where the provider will send completion notification"
    )

    job_type = fields.Selection(
        [
            ('image_generation', 'Image Generation'),
            ('video_generation', 'Video Generation'),
            ('audio_generation', 'Audio Generation'),
            ('text_generation', 'Text Generation'),
            ('media_generation', 'Media Generation'),
        ],
        string="Job Type",
        default='media_generation',
        required=True,
        tracking=True,
        help="Type of generation job"
    )

    # Job tracking
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("queued", "Queued"),
            ("processing", "Processing"),
            ("completed", "Completed"),
            ("failed", "Failed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        string="Status",
        tracking=True,
    )

    # External job details
    external_job_id = fields.Char(
        string="External Job ID",
        tracking=True,
        help="ID of the job on the provider's system (e.g., request_id from FAL)"
    )
    
    gateway_request_id = fields.Char(
        string="Gateway Request ID",
        tracking=True,
        help="Gateway request ID from the provider (if different from external_job_id)"
    )

    # Timestamps
    submitted_date = fields.Datetime(
        string="Submitted Date",
        tracking=True,
        help="Date when the job was submitted to the provider"
    )
    started_date = fields.Datetime(
        string="Started Date",
        tracking=True,
        help="Date when the job started processing"
    )
    completed_date = fields.Datetime(
        string="Completed Date",
        tracking=True,
        help="Date when the job was completed"
    )

    # Results
    result_payload = fields.Json(
        string="Result Payload",
        help="JSON response from the provider containing the generated content"
    )
    
    error_message = fields.Text(
        string="Error Message",
        tracking=True,
        help="Error message if the job failed"
    )

    # Visibility in lists
    visible_in_tree = fields.Boolean(
        string="Visible in Tree",
        default=True,
        help="Whether this job should be visible in tree/list views"
    )

    # Processing metadata
    retry_count = fields.Integer(
        string="Retry Count",
        default=0,
        help="Number of times this job has been retried"
    )
    
    max_retries = fields.Integer(
        string="Max Retries",
        default=3,
        help="Maximum number of retries allowed"
    )

    @api.model
    def create(self, vals):
        """Generate a default name if not provided"""
        if not vals.get('name'):
            vals['name'] = f"Generation Job {fields.Datetime.now()}"
        return super().create(vals)

    def action_submit(self):
        """Submit the job to the provider"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError("Only draft jobs can be submitted")
        
        self._submit_to_provider()
        return True

    def action_cancel(self):
        """Cancel the job"""
        self.ensure_one()
        if self.state in ['completed', 'failed', 'cancelled']:
            raise UserError("Cannot cancel a job that is already finished")
        
        # Try to cancel with provider if it has an external ID
        if self.external_job_id and self.provider_id:
            try:
                self.provider_id.cancel_generation_job(self.external_job_id)
            except Exception as e:
                _logger.warning(f"Failed to cancel job {self.external_job_id} with provider: {e}")
        
        self.write({
            'state': 'cancelled',
            'completed_date': fields.Datetime.now()
        })
        return True

    def action_retry(self):
        """Retry a failed job"""
        self.ensure_one()
        if self.state != 'failed':
            raise UserError("Only failed jobs can be retried")
        
        if self.retry_count >= self.max_retries:
            raise UserError(f"Maximum number of retries ({self.max_retries}) exceeded")
        
        self.write({
            'state': 'draft',
            'retry_count': self.retry_count + 1,
            'error_message': False,
            'external_job_id': False,
            'gateway_request_id': False,
            'submitted_date': False,
            'started_date': False,
            'completed_date': False,
            'result_payload': False,
        })
        
        return self.action_submit()

    def action_hide_from_tree(self):
        """Hide completed jobs from tree view"""
        self.ensure_one()
        if self.state in ['completed', 'failed', 'cancelled']:
            self.visible_in_tree = False

    def action_check_status(self):
        """Check the status of the job with the provider"""
        self.ensure_one()
        if not self.external_job_id:
            raise UserError("No external job ID found")

        return self.provider_id._dispatch("check_generation_job_status",self)

    def _submit_to_provider(self):
        """Submit the job to the provider"""
        self.ensure_one()
        
        # Generate webhook URL if not provided
        if not self.webhook_url:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            self.webhook_url = f"{base_url}/llm/generate_job/webhook/{self.id}"
        
        # Submit to provider
        result = self.provider_id.submit_generation_job(self)
        
        # Update job with provider response
        vals = {
            'state': 'submitted',
            'submitted_date': fields.Datetime.now(),
            'external_job_id': result.get('request_id'),
            'gateway_request_id': result.get('gateway_request_id'),
        }
        
        # If provider indicates immediate processing
        if result.get('status') == 'processing':
            vals['state'] = 'processing'
            vals['started_date'] = fields.Datetime.now()
        
        self.write(vals)
        
        _logger.info(f"Generation job '{self.name}' submitted successfully. "
                    f"External job ID: {result.get('request_id')}")

    def process_webhook_result(self, webhook_data):
        """Process webhook result from provider"""
        self.ensure_one()
        
        status = webhook_data.get('status')
        
        if status == 'OK':
            # Success
            self.write({
                'state': 'completed',
                'completed_date': fields.Datetime.now(),
                'result_payload': webhook_data.get('payload'),
            })
            
            # Send result to thread
            self._send_result_to_thread(webhook_data.get('payload'))
            
        elif status == 'ERROR':
            # Error
            self.write({
                'state': 'failed',
                'completed_date': fields.Datetime.now(),
                'error_message': webhook_data.get('error', 'Unknown error'),
                'result_payload': webhook_data.get('payload'),  # May contain error details
            })
            
            # Notify thread about error
            self._send_error_to_thread(webhook_data.get('error', 'Unknown error'))
        
        else:
            _logger.warning(f"Unknown webhook status '{status}' for job {self.id}")

    def _send_result_to_thread(self, payload):
        """Send successful generation result to the thread"""
        self.ensure_one()
        
        if not self.thread_id:
            _logger.error(f"No thread found for job {self.id}")
            return
        
        try:            # Format the result for the thread
            formatted_result = self._format_result_for_thread(payload)
            
            # Post message to thread
            message = self.thread_id._post_message(
                body=formatted_result.get('body', 'Generation completed'),
                attachment_ids=formatted_result.get('attachment_ids', []),
                subtype_xmlid=LLM_ASSISTANT_SUBTYPE_XMLID
            )
            self._send_realtime_notification(message)
            
        except Exception as e:
            _logger.error(f"Failed to send result to thread {self.thread_id.id}: {e}")

    def _send_error_to_thread(self, error_message):
        """Send error notification to the thread"""
        self.ensure_one()
        
        if not self.thread_id:
            return
        
        try:
            body = f"❌ Generation failed: {error_message}"
            message = self.thread_id.message_post(
                body=body,
                subtype_xmlid='llm_mail_message_subtypes.llm_assistant'
            )

            # Send real-time notification to refresh the thread
            self._send_realtime_notification(message)
        except Exception as e:
            _logger.error(f"Failed to send error to thread {self.thread_id.id}: {e}")

    def _format_result_for_thread(self, payload):
        """Format the generation result for posting to thread"""
        self.ensure_one()
        
        # This will need to be customized based on the type of generation
        # For now, handle common cases like images
        
        body_parts = []
        attachment_ids = []
        
        if isinstance(payload, dict):
            # Handle image generation results
            if 'images' in payload:
                body_parts.append("🎨 **Generation completed!**")
                for i, image in enumerate(payload['images']):
                    if isinstance(image, dict) and 'url' in image:
                        # Create attachment from URL
                        try:
                            attachment = self._create_attachment_from_url(
                                image['url'], 
                                image.get('file_name', f'generated_image_{i+1}.png')
                            )
                            if attachment:
                                attachment_ids.append(attachment.id)
                                body_parts.append(f"![Generated Image {i+1}]({image['url']})")
                        except Exception as e:
                            _logger.error(f"Failed to create attachment from URL {image['url']}: {e}")
                            body_parts.append(f"[Generated Image {i+1}]({image['url']})")
            
            # Handle video generation results  
            elif 'video' in payload:
                body_parts.append("🎬 **Video generation completed!**")
                video = payload['video']
                if isinstance(video, dict) and 'url' in video:
                    try:
                        attachment = self._create_attachment_from_url(
                            video['url'],
                            video.get('file_name', 'generated_video.mp4')
                        )
                        if attachment:
                            attachment_ids.append(attachment.id)
                        body_parts.append(f"[Generated Video]({video['url']})")
                    except Exception as e:
                        _logger.error(f"Failed to create attachment from URL {video['url']}: {e}")
                        body_parts.append(f"[Generated Video]({video['url']})")
            
            # Handle generic results
            else:
                body_parts.append("✅ **Generation completed!**")
                body_parts.append(f"```json\n{json.dumps(payload, indent=2)}\n```")
        
        else:
            body_parts.append("✅ **Generation completed!**")
            body_parts.append(str(payload))
        
        return {
            'body': '\n\n'.join(body_parts),
            'attachment_ids': attachment_ids
        }

    def _create_attachment_from_url(self, url, filename):
        """Create an attachment from a URL"""
        try:
            return self.env['ir.attachment'].create({
                'name': filename,
                'type': 'url',
                'url': url,
                'res_model': self._name,
                'res_id': self.id,
            })
        except Exception as e:
            _logger.error(f"Failed to create attachment from URL {url}: {e}")
            return None

    @api.model
    def cleanup_completed_jobs(self, days_old=7):
        """Cleanup old completed jobs (called by cron)"""
        cutoff_date = fields.Datetime.now() - timedelta(days=days_old)
        
        jobs_to_hide = self.search([
            ('state', 'in', ['completed', 'failed', 'cancelled']),
            ('completed_date', '<', cutoff_date),
            ('visible_in_tree', '=', True)
        ])
        
        jobs_to_hide.write({'visible_in_tree': False})
        
        _logger.info(f"Hidden {len(jobs_to_hide)} old generation jobs from tree view")
        
        return len(jobs_to_hide)

    def _auto_hide_completed_jobs(self):
        """Automatically hide completed jobs from tree view"""
        if self.state in ['completed', 'failed'] and self.visible_in_tree:
            self.visible_in_tree = False
            _logger.info(f"Auto-hiding completed job {self.id} from tree view")

    def write(self, vals):
        """Override write to auto-hide completed jobs"""
        result = super().write(vals)
        
        # Auto-hide jobs when they complete
        if 'state' in vals and vals['state'] in ['completed', 'failed']:
            self._auto_hide_completed_jobs()
        
        return result

    def _send_realtime_notification(self, message):
        """Send real-time notification to update the thread interface"""
        self.ensure_one()
        
        if not message or not self.thread_id:
            return
        
        try:
            # Send notification through Odoo's bus system
            channel = f"llm_thread_{self.thread_id.id}"
            
            # Prepare notification payload
            notification = {
                'type': 'new_message',
                'thread_id': self.thread_id.id,
                'message_id': message.id,
                'job_id': self.id,
                'message': {
                    'id': message.id,
                    'body': message.body,
                    'date': message.date.isoformat() if message.date else None,
                    'author_id': [message.author_id.id, message.author_id.name] if message.author_id else None,
                    'attachment_ids': message.attachment_ids.ids,
                }
            }
            
            # Send via bus using the Odoo 16 method
            self.env['bus.bus']._sendone(
                [self.env.user.partner_id], 
                'llm_thread_update', 
                notification
            )
            
            _logger.info(f"Sent real-time notification for job {self.id} to channel {channel}")
            
        except Exception as e:
            _logger.error(f"Failed to send real-time notification for job {self.id}: {e}")
