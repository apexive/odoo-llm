import logging

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
        default=dict,
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
            "Training job '%s' submitted successfully. External job ID: %s",
            self.name,
            training_job_id,
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
        self.write({"training_metrics": metrics})
        return True
