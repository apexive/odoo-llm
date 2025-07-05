import logging
import tempfile
import zipfile
import os
import base64
import requests
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class LLMThread(models.Model):
    _inherit = "llm.thread"

    # Computed field for zip URL of user image attachments
    all_user_image_attachments_zip = fields.Char(
        string="User Images Zip URL",
        compute="_compute_all_user_image_attachments_zip",
        help="URL to zip file containing all image attachments from USER messages"
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to trigger avatar training when conditions are met"""
        threads = super().create(vals_list)
        
        # Don't trigger training immediately on create since there are no messages yet
        # The training will be triggered when messages are added
        
        return threads

    def _check_and_create_avatar_training(self, force=False):
        """Check if thread meets criteria for avatar training and create training job if needed"""
        try:
            # Check if thread has an assistant
            if not self.assistant_id:
                return
            
            # Check if assistant has a prompt with category "train_avatar"
            assistant = self.assistant_id
            if not assistant.prompt_id or not assistant.prompt_id.category_id:
                return
            
            # Check if category code is "train_avatar"
            if assistant.prompt_id.category_id.code != "train_avatar":
                return
            
            # Check if we have a model with image_generation capability
            model = self.model_id
            if not model or model.model_use != 'image_generation':
                _logger.warning(
                    f"Thread {self.id}: Model {model.name if model else 'None'} "
                    f"does not support image_generation. Avatar training skipped."
                )
                # Only post error if force is True (user explicitly requested training)
                if force:
                    self._post_training_error_message(
                        "Error: The selected model does not support image generation. "
                        "Please select a model with model_use = 'image_generation' to train avatars."
                    )
                return
            
            # Check if we have user messages with image attachments
            user_messages = self.message_ids.filtered(
                lambda m:
                         m.attachment_ids.filtered(lambda a: a.mimetype and a.mimetype.startswith('image/'))
            )
            
            if not user_messages:
                if force:
                    self._post_training_error_message(
                        "Error: No user messages with images found. "
                        "Please add some images to the messages before training the avatar."
                    )
                return
            
            # Check if training job already exists for this thread
            existing_job = self.env['llm.training.job'].search([
                ('name', 'ilike', f'Avatar Training - {self.name}'),
                ('state', 'in', ['draft', 'validating', 'preparing', 'queued', 'training'])
            ], limit=1)
            
            if existing_job:
                _logger.info(f"Thread {self.id}: Avatar training job already exists ({existing_job.id})")
                return
            
            # Create avatar training job
            self._create_avatar_training_job(assistant, model)
            
        except Exception as e:
            _logger.error(f"Error checking avatar training conditions for thread {self.id}: {e}")

    def trigger_avatar_training(self):
        """Manually trigger avatar training for this thread"""
        self._check_and_create_avatar_training(force=True)

    def _create_avatar_training_job(self, assistant, model):
        """Create and start avatar training job"""
        try:
            # Create training job
            training_job = self.env['llm.training.job'].create({
                'name': f"Avatar Training - {self.name}",
                'description': f"Automatic avatar training for thread {self.name} with assistant {assistant.name}",
                'provider_id': self.provider_id.id,
                'base_model_id': model.id,
                'state': 'draft',
                'hyperparameters': {
                    'create_masks': True,
                    'steps': 1000,
                    'trigger_word': ""
                }
            })
            
            # Start the avatar training process
            training_job.start_avatar_training(self, assistant)
            
            _logger.info(f"Avatar training job {training_job.id} created for thread {self.id}")
            
        except Exception as e:
            _logger.error(f"Error creating avatar training job for thread {self.id}: {e}")
            self._post_training_error_message(
                f"Error al crear el trabajo de entrenamiento: {str(e)}"
            )

    def _post_message(self, **kwargs):
        """Override to trigger avatar training when user messages with images are added"""
        result = super()._post_message(**kwargs)
        
        # Check if this is a user message with image attachments
        subtype_xmlid = kwargs.get('subtype_xmlid')
        attachment_ids = kwargs.get('attachment_ids', [])
        
        if (subtype_xmlid == "llm_mail_message_subtypes.mt_llm_user" and 
            attachment_ids and 
            self.assistant_id and 
            self.assistant_id.prompt_id and 
            self.assistant_id.prompt_id.category_id and 
            self.assistant_id.prompt_id.category_id.code == "train_avatar"):
            
            # Check if any of the attachments are images
            has_images = False
            for attachment_id in attachment_ids:
                if isinstance(attachment_id, (list, tuple)) and len(attachment_id) > 2:
                    # Handle [(4, id)] or [(0, 0, values)] format
                    continue
                attachment = self.env['ir.attachment'].browse(attachment_id)
                if attachment.mimetype and attachment.mimetype.startswith('image/'):
                    has_images = True
                    break
            
            if has_images:
                # Trigger avatar training check (without delay for simplicity)
                try:
                    self._check_and_create_avatar_training()
                except Exception as e:
                    _logger.error(f"Error triggering avatar training: {e}")
        
        return result

    def _post_training_error_message(self, error_message):
        """Post error message to thread"""
        try:
            self._post_message(
                subtype_xmlid="llm_mail_message_subtypes.mt_llm_assistant",
                body=error_message,
                author_id=False,
            )
        except Exception as e:
            _logger.error(f"Error posting training error message to thread {self.id}: {e}")

    def _compute_all_user_image_attachments_zip(self):
        """Compute the zip URL for all user image attachments"""
        for thread in self:
            thread.all_user_image_attachments_zip = thread._get_user_image_attachments_zip_url()

    def _get_user_image_attachments_zip_url(self):
        """Get all image attachments from USER messages, create zip, upload to fal.ai, return URL"""
        try:
            # Get all USER messages with image attachments
            user_messages = self.message_ids.filtered(
                lambda m:   m.attachment_ids
            )
            
            if not user_messages:
                _logger.info(f"Thread {self.id}: No USER messages with attachments found")
                return False
            
            # Collect all image attachments from USER messages
            image_attachments = self.env['ir.attachment']
            for message in user_messages:
                for attachment in message.attachment_ids:
                    if attachment.mimetype and attachment.mimetype.startswith('image/'):
                        image_attachments |= attachment
            
            if not image_attachments:
                _logger.info(f"Thread {self.id}: No image attachments found in USER messages")
                return False
            
            # Create zip file with all images
            zip_url = self._create_and_upload_images_zip(image_attachments)
            return zip_url
            
        except Exception as e:
            _logger.error(f"Error creating user image attachments zip for thread {self.id}: {e}")
            return False

    def _create_and_upload_images_zip(self, image_attachments):
        """Create a zip file with images and upload to fal.ai"""
        zip_url = False
        try:
            # Create temporary zip file
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_zip:
                with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for i, attachment in enumerate(image_attachments):
                        # Get file extension from mimetype
                        ext = self._get_extension_from_mimetype(attachment.mimetype)
                        filename = f"image_{i+1:03d}{ext}"
                        
                        # Add image to zip
                        zipf.writestr(filename, attachment.raw)
                        _logger.info(f"Added {filename} to zip for thread {self.id}")
                
                # Upload zip to fal.ai and get URL
                zip_url = self._upload_zip_to_fal_ai(temp_zip.name)

            return zip_url
                
        except Exception as e:
            _logger.error(f"Error creating and uploading images zip for thread {self.id}: {e}")
            raise UserError(f"Error creating images zip: {str(e)}")

    def _get_extension_from_mimetype(self, mimetype):
        """Get file extension from mimetype"""
        extensions = {
            'image/jpeg': '.jpg',
            'image/jpg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'image/bmp': '.bmp',
            'image/tiff': '.tiff'
        }
        return extensions.get(mimetype, '.jpg')

    def _upload_zip_to_fal_ai(self, zip_file_path):
        """Upload zip file to fal.ai and return URL"""
        try:
            # Get fal.ai provider
            fal_ai_provider = self.env['llm.provider'].search([
                ('service', '=', 'fal_ai')
            ], limit=1)
            
            if not fal_ai_provider:
                raise UserError("No fal.ai provider configured")
            
            # Get fal.ai client
            fal_client = fal_ai_provider.fal_ai_get_client()
            
            # Upload file to fal.ai
            return fal_client.upload_file(zip_file_path)
                

        except Exception as e:
            _logger.error(f"Error uploading zip to fal.ai: {e}")
            raise UserError(f"Error uploading zip to fal.ai: {str(e)}")
