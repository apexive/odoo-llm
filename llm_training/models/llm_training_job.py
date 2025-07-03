import json
import logging
import base64
import requests
import tempfile
import zipfile
import os

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class LLMTrainingJob(models.Model):
    _name = "llm.training.job"
    _description = "LLM Fine-tuning Job"
    _inherit = ["mail.thread"]
    _order = "id desc"

    name = fields.Char(required=True, tracking=True)
    description = fields.Text(tracking=True)
    active = fields.Boolean(default=True)

    # Provider information
    provider_id = fields.Many2one(
        "llm.provider", string="LLM Provider", required=True, tracking=True
    )
    base_model_id = fields.Many2one(
        "llm.model",
        string="Base Model",
        required=True,
        domain="[('provider_id', '=', provider_id)]",
        tracking=True,
    )
    trained_model_name = fields.Char(
        string="Trained Model Name", tracking=True, help="Name of the fine-tuned model"
    )

    # Job details and tracking
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("validating", "Validating"),
            ("preparing", "Preparing"),
            ("queued", "Queued"),
            ("training", "Training"),
            ("completed", "Completed"),
            ("failed", "Failed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        string="Status",
        tracking=True,
    )

    # Job configuration
    hyperparameters = fields.Json(
        string="Hyperparameters",
        default={},
        help="Training hyperparameters (epochs, batch size, etc.)",
    )

    # Dataset relation
    dataset_ids = fields.Many2many(
        "llm.training.dataset",
        "llm_training_job_dataset_rel",
        "job_id",
        "dataset_id",
        string="Datasets",
        required=True,
    )

    # Results and metrics
    external_job_id = fields.Char(
        string="External Job ID",
        tracking=True,
        help="ID of the job on the provider's system",
    )
    training_metrics = fields.Json(
        string="Training Metrics",
        help="Metrics from the training job (loss, accuracy, etc.)",
        tracking=True,
    )
    training_logs = fields.Text(
        string="Training Logs", help="Logs from the training process"
    )

    # Costs
    estimated_cost = fields.Float(
        string="Estimated Cost",
        compute="_compute_estimated_cost",
        store=False,
        help="Estimated cost of the training job in USD",
    )
    final_cost = fields.Float(
        string="Final Cost", tracking=True, help="Final cost of the training job in USD"
    )

    # Result model details
    result_model_id = fields.Many2one(
        "llm.model",
        string="Resulting Model",
        help="The fine-tuned model created by this job",
    )

    @api.depends("dataset_ids", "base_model_id")
    def _compute_estimated_cost(self):
        """Calculate estimated cost based on dataset size and model"""
        # TODO: Think about it later
        for record in self:
            # This would use provider-specific pricing information
            # For demonstration, using a simplified calculation
            example_count = sum(dataset.example_count for dataset in record.dataset_ids)
            base_cost = 0.0

            # Different providers have different pricing structures
            if record.provider_id and record.provider_id.service:
                if record.provider_id.service == "openai":
                    # Example OpenAI pricing
                    if record.base_model_id and "gpt-4" in record.base_model_id.name:
                        base_cost = 0.03 * example_count  # $0.03 per 1K tokens
                    else:
                        base_cost = 0.008 * example_count  # $0.008 per 1K tokens

            record.estimated_cost = base_cost

    def action_submit(self):
        """Submit job to the provider"""
        self.ensure_one()
        self._submit()
        return True

    def _submit(self):
        self.provider_id.validate_datasets(self)
        result = self.provider_id.start_training_job(self)
        training_job_id = result.get("training_job_id")
        if not training_job_id:
            raise UserError(f"Job '{self.name}': No training job ID found.")

        self.write(
            {
                "state": "validating",
                "external_job_id": training_job_id,
            }
        )

        _logger.info(
            f"Training job '{self.name}' submitted successfully. External job ID: {training_job_id}"
        )

    def action_cancel(self):
        """Cancel the training job"""
        self.ensure_one()
        self.provider_id.cancel_training_job(job_id=self.external_job_id)
        self.write({"state": "cancelled"})
        return True

    def action_check_status(self):
        """Check the status of the job with the provider"""
        result = self._check_status()

        return result

    def _check_status(self):
        self.ensure_one()
        # TODO: For now it supports openai format but it should be uniform structure
        result = self.provider_id.check_training_job_status(self)

        if result.get("state") == "completed":
            self.write(
                {
                    "state": result.get("state"),
                    "result_model_id": result.get("result_model_id"),
                    "trained_model_name": result.get("trained_model_name"),
                }
            )
        else:
            self.write({"state": result.get("state")})
        self.update_training_metrics(result.get("response"))
        return True

    def update_training_metrics(self, metrics):
        """Update training metrics from the provider"""
        self.ensure_one()

        # Convert metrics dict to JSON string due to lack of widget support
        if isinstance(metrics, dict):
            metrics_str = json.dumps(metrics, indent=2)
        else:
            metrics_str = str(metrics)

        self.write({"training_metrics": metrics_str})
        return True

    # Avatar training specific methods
    def start_avatar_training(self, thread, assistant):
        """Start avatar training workflow for a thread"""
        try:
            # Set job state to preparing
            self.write({'state': 'preparing'})
            
            # Get the zip URL for user image attachments
            zip_url = thread._get_user_image_attachments_zip_url()
            
            if not zip_url:
                raise UserError("No se encontraron imágenes en los mensajes del usuario")
            
            # Prepare training parameters using the prompt template
            training_params = self._prepare_avatar_training_params(assistant, zip_url)
            
            # Start the training job
            self._submit_avatar_training_job(training_params, thread)
            
        except Exception as e:
            _logger.error(f"Error starting avatar training for job {self.id}: {e}")
            self.write({'state': 'failed'})
            # Post error message to thread
            thread._post_training_error_message(
                f"Error al iniciar el entrenamiento de avatar: {str(e)}"
            )
            raise

    def _prepare_avatar_training_params(self, assistant, zip_url):
        """Prepare training parameters from assistant prompt template"""
        try:
            # Get the prompt template
            prompt_template = assistant.prompt_id.template
            
            # Parse the template to extract parameters
            # The template should contain the JSON structure with placeholders
            import json
            
            # Replace the placeholder with actual zip URL
            prepared_template = prompt_template.replace(
                "{{ related_record.all_user_image_attachments_zip }}", 
                f'"{zip_url}"'
            )
            
            # Parse JSON to validate structure
            try:
                training_params = json.loads(prepared_template)
            except json.JSONDecodeError:
                # If not valid JSON, create default structure
                training_params = {
                    "images_data_url": zip_url,
                    "create_masks": True,
                    "steps": 1000,
                    "trigger_word": ""
                }
            
            # Ensure required fields are present
            if 'images_data_url' not in training_params:
                training_params['images_data_url'] = zip_url
            
            if 'create_masks' not in training_params:
                training_params['create_masks'] = True
                
            if 'steps' not in training_params:
                training_params['steps'] = 1000
                
            if 'trigger_word' not in training_params:
                training_params['trigger_word'] = ""
            
            return training_params
            
        except Exception as e:
            _logger.error(f"Error preparing avatar training params: {e}")
            raise UserError(f"Error preparando parámetros de entrenamiento: {str(e)}")

    def _submit_avatar_training_job(self, training_params, thread):
        """Submit avatar training job to fal.ai"""
        try:
            # Get fal.ai provider
            fal_ai_provider = self.env['llm.provider'].search([
                ('service', '=', 'fal_ai')
            ], limit=1)
            
            if not fal_ai_provider:
                raise UserError("No se encontró un proveedor fal.ai configurado")
            
            # Get fal.ai client
            fal_client = fal_ai_provider.fal_ai_get_client()
            
            # Set job state to queued
            self.write({'state': 'queued'})
            
            # Submit training job to fal.ai asynchronously
            # Use commit_asynchronously to run in background
            self.env.cr.commit()
            
            # Run training in a separate method that can be called asynchronously
            try:
                self._run_avatar_training_sync(fal_client, training_params, thread.id)
            except Exception as e:
                _logger.error(f"Error in synchronous training: {e}")
                # Try to continue with async processing
                self.with_context(async_mode=True)._run_avatar_training_async(fal_client, training_params, thread.id)
            
            _logger.info(f"Avatar training job {self.id} submitted successfully")
            
        except Exception as e:
            _logger.error(f"Error submitting avatar training job {self.id}: {e}")
            self.write({'state': 'failed'})
            raise

    def _run_avatar_training_sync(self, fal_client, training_params, thread_id):
        """Run avatar training synchronously"""
        try:
            # Set job state to training
            self.write({'state': 'training'})
            
            # Submit training job to fal.ai
            result = fal_client.subscribe(
                "fal-ai/flux-lora-fast-training",
                arguments=training_params,
                with_logs=True,
            )
            
            if not result:
                raise UserError("No se recibió respuesta del entrenamiento")
            
            # Process training result
            self._process_avatar_training_result(result, thread_id)
            
        except Exception as e:
            _logger.error(f"Error running avatar training sync for job {self.id}: {e}")
            self.write({'state': 'failed'})
            
            # Post error message to thread
            thread = self.env['llm.thread'].browse(thread_id)
            if thread.exists():
                thread._post_training_error_message(
                    f"Error durante el entrenamiento: {str(e)}"
                )
            raise

    @api.model
    def _run_avatar_training_async(self, fal_client, training_params, thread_id):
        """Run avatar training asynchronously"""
        try:
            # Set job state to training
            self.write({'state': 'training'})
            
            # Submit training job to fal.ai
            result = fal_client.subscribe(
                "fal-ai/flux-lora-fast-training",
                arguments=training_params,
                with_logs=True,
            )
            
            if not result:
                raise UserError("No se recibió respuesta del entrenamiento")
            
            # Process training result
            self._process_avatar_training_result(result, thread_id)
            
        except Exception as e:
            _logger.error(f"Error running avatar training async for job {self.id}: {e}")
            self.write({'state': 'failed'})
            
            # Post error message to thread
            thread = self.env['llm.thread'].browse(thread_id)
            if thread.exists():
                thread._post_training_error_message(
                    f"Error durante el entrenamiento: {str(e)}"
                )

    def _process_avatar_training_result(self, result, thread_id):
        """Process the training result and post to thread"""
        try:
            # Get thread
            thread = self.env['llm.thread'].browse(thread_id)
            if not thread.exists():
                raise UserError(f"Thread {thread_id} no encontrado")
            
            # Extract model file from result
            if not result.get('diffusers_lora_file'):
                raise UserError("No se encontró el archivo del modelo LoRA en el resultado")
            
            model_file_info = result['diffusers_lora_file']
            model_url = model_file_info.get('url')
            model_filename = model_file_info.get('file_name', 'lora_model.safetensors')
            
            if not model_url:
                raise UserError("No se encontró la URL del modelo LoRA")
            
            # Download and attach model to thread
            self._download_and_attach_model(model_url, model_filename, thread)
            
            # Update job state
            self.write({
                'state': 'completed',
                'trained_model_name': model_filename
            })
            _logger.info(f"Avatar training job {self.id} completed successfully")
        except Exception as e:
            _logger.error(f"Error processing avatar training result for job {self.id}: {e}")
            self.write({'state': 'failed'})
            raise

    def _download_and_attach_model(self, model_url, model_filename, thread):
        """Download LoRA model and attach to thread"""
        try:
            # Download model file
            response = requests.get(model_url, stream=True)
            response.raise_for_status()
            
            # Create attachment
            attachment = self.env['ir.attachment'].create({
                'name': model_filename,
                'datas': base64.b64encode(response.content),
                'res_model': 'llm.thread',
                'res_id': thread.id,
                'mimetype': 'application/octet-stream',
                'description': f'Modelo LoRA entrenado para avatar - Job {self.id}'
            })
            
            # Post message with attachment
            thread._post_message(
                subtype_xmlid="llm_mail_message_subtypes.mt_llm_assistant",
                body=f"Modelo LoRA descargado: {model_filename}",
                author_id=False,
                attachment_ids=[attachment.id]
            )
            
            _logger.info(f"Model {model_filename} downloaded and attached to thread {thread.id}")
            
        except Exception as e:
            _logger.error(f"Error downloading and attaching model: {e}")
            raise UserError(f"Error descargando modelo: {str(e)}")
