import logging
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class LLMGenerationJob(models.Model):
    _name = "llm.generation.job"
    _description = "LLM Generation Job"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"
    _rec_name = "display_name"

    # Job identification
    name = fields.Char(
        string="Job Name",
        compute="_compute_name",
        store=True,
        help="Auto-generated job name based on thread and model",
    )
    display_name = fields.Char(
        string="Display Name",
        compute="_compute_display_name",
        store=True,
    )

    # Relationships
    thread_id = fields.Many2one(
        "llm.thread",
        string="Thread",
        required=True,
        ondelete="cascade",
        help="Thread that this generation job belongs to",
    )
    provider_id = fields.Many2one(
        "llm.provider",
        string="Provider",
        required=True,
        help="LLM provider handling this job",
    )
    model_id = fields.Many2one(
        "llm.model", string="Model", required=True, help="LLM model used for generation"
    )

    # Job status
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("queued", "Queued"),
            ("running", "Running"),
            ("completed", "Completed"),
            ("failed", "Failed"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )

    # Message relationships
    input_message_id = fields.Many2one(
        "mail.message",
        string="Input Message",
        help="Message that triggered this generation job",
    )
    output_message_id = fields.Many2one(
        "mail.message",
        string="Output Message",
        help="Message created by this generation job",
    )

    # Provider-specific data
    external_job_id = fields.Char(
        string="External Job ID", help="Provider's job identifier"
    )
    provider_data = fields.Json(
        string="Provider Data", help="Provider-specific metadata and configuration"
    )

    # Generation inputs
    generation_inputs = fields.Json(
        string="Generation Inputs", help="Input data for the generation process"
    )

    # Timing fields
    queued_at = fields.Datetime(string="Queued At", help="When the job was queued")
    started_at = fields.Datetime(
        string="Started At", help="When the job started processing"
    )
    completed_at = fields.Datetime(
        string="Completed At", help="When the job completed (success or failure)"
    )

    # Duration computation
    duration = fields.Float(
        string="Duration (seconds)",
        compute="_compute_duration",
        store=True,
        help="Total processing time in seconds",
    )
    queue_duration = fields.Float(
        string="Queue Duration (seconds)",
        compute="_compute_queue_duration",
        store=True,
        help="Time spent in queue before processing",
    )

    # Error handling
    error_message = fields.Text(
        string="Error Message", help="Error details if job failed"
    )
    retry_count = fields.Integer(
        string="Retry Count", default=0, help="Number of retry attempts"
    )
    max_retries = fields.Integer(
        string="Max Retries", default=3, help="Maximum number of retry attempts"
    )

    # User and creation info
    user_id = fields.Many2one(
        "res.users",
        string="User",
        default=lambda self: self.env.user,
        required=True,
        help="User who initiated the generation",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )

    # Computed fields
    is_active = fields.Boolean(
        string="Is Active",
        compute="_compute_is_active",
        help="True if job is in an active state (queued or running)",
    )
    can_retry = fields.Boolean(
        string="Can Retry",
        compute="_compute_can_retry",
        help="True if job can be retried",
    )
    can_cancel = fields.Boolean(
        string="Can Cancel",
        compute="_compute_can_cancel",
        help="True if job can be cancelled",
    )

    @api.depends("thread_id", "model_id", "create_date")
    def _compute_name(self):
        for job in self:
            if job.thread_id and job.model_id:
                job.name = f"{job.thread_id.name} - {job.model_id.name}"
            else:
                job.name = f"Generation Job {job.id}"

    @api.depends("name", "state", "create_date")
    def _compute_display_name(self):
        for job in self:
            if job.name:
                job.display_name = f"{job.name} ({job.state})"
            else:
                job.display_name = f"Generation Job {job.id} ({job.state})"

    @api.depends("state")
    def _compute_is_active(self):
        for job in self:
            job.is_active = job.state in ["queued", "running"]

    @api.depends("state", "retry_count", "max_retries")
    def _compute_can_retry(self):
        for job in self:
            job.can_retry = job.state == "failed" and job.retry_count < job.max_retries

    @api.depends("state")
    def _compute_can_cancel(self):
        for job in self:
            job.can_cancel = job.state in ["queued", "running"]

    @api.depends("started_at", "completed_at")
    def _compute_duration(self):
        for job in self:
            if job.started_at and job.completed_at:
                delta = job.completed_at - job.started_at
                job.duration = delta.total_seconds()
            else:
                job.duration = 0.0

    @api.depends("queued_at", "started_at")
    def _compute_queue_duration(self):
        for job in self:
            if job.queued_at and job.started_at:
                delta = job.started_at - job.queued_at
                job.queue_duration = delta.total_seconds()
            else:
                job.queue_duration = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set default values and validate data"""
        for vals in vals_list:
            # Set default provider and model from thread if not provided
            if "thread_id" in vals and not vals.get("provider_id"):
                thread = self.env["llm.thread"].browse(vals["thread_id"])
                vals["provider_id"] = thread.provider_id.id
                vals["model_id"] = thread.model_id.id

        return super().create(vals_list)

    def write(self, vals):
        """Override write to handle state transitions"""
        # Handle state transitions
        if "state" in vals:
            current_time = fields.Datetime.now()

            # Set timing fields based on state transitions
            if vals["state"] == "queued" and not vals.get("queued_at"):
                vals["queued_at"] = current_time
            elif vals["state"] == "running" and not vals.get("started_at"):
                vals["started_at"] = current_time
            elif vals["state"] in ["completed", "failed", "cancelled"] and not vals.get(
                "completed_at"
            ):
                vals["completed_at"] = current_time

        return super().write(vals)

    def action_queue(self):
        """Queue the generation job"""
        self.ensure_one()
        if self.state != "draft":
            raise UserError(
                _(
                    "This generation request has already been submitted and cannot be queued again."
                )
            )

        self.write(
            {
                "state": "queued",
                "queued_at": fields.Datetime.now(),
            }
        )

        # Trigger queue processing
        self.env["llm.generation.queue"]._process_model_queue(self.model_id)

        return True

    def action_start(self):
        """Start processing the generation job"""
        self.ensure_one()
        if self.state != "queued":
            raise UserError(
                _(
                    "This generation request is not ready to start. "
                    "It may have already completed or been cancelled."
                )
            )

        self.write(
            {
                "state": "running",
                "started_at": fields.Datetime.now(),
            }
        )

        # Call provider to start generation
        try:
            external_job_id = self.provider_id.create_generation_job(self)
            self.write({"external_job_id": external_job_id})
        except Exception as e:
            self.write(
                {
                    "state": "failed",
                    "error_message": str(e),
                    "completed_at": fields.Datetime.now(),
                }
            )
            raise

    def action_cancel(self):
        """Cancel the generation job"""
        self.ensure_one()
        if not self.can_cancel:
            raise UserError(
                _(
                    "This request cannot be cancelled because it has already completed or finished processing."
                )
            )

        # Try to cancel with provider if running
        if self.state == "running" and self.external_job_id:
            try:
                self.provider_id.cancel_generation_job(self)
            except Exception as e:
                _logger.warning(f"Failed to cancel job {self.id} with provider: {e}")

        self.write(
            {
                "state": "cancelled",
                "completed_at": fields.Datetime.now(),
            }
        )

    def action_retry(self):
        """Retry a failed generation job"""
        self.ensure_one()
        if not self.can_retry:
            raise UserError(
                _(
                    "This request cannot be retried. It may have exceeded the maximum retry "
                    "limit or is not in a failed state."
                )
            )

        # Reset job state for retry
        # Inputs will be prepared fresh at execution time
        self.write(
            {
                "state": "queued",
                "retry_count": self.retry_count + 1,
                "queued_at": fields.Datetime.now(),
                "started_at": False,
                "completed_at": False,
                "error_message": False,
                "external_job_id": False,
            }
        )

        # Trigger queue processing
        self.env["llm.generation.queue"]._process_model_queue(self.model_id)

        return True

    def action_complete(self, output_message_id=None):
        """Mark job as completed"""
        self.ensure_one()
        if self.state != "running":
            raise UserError(
                _(
                    "Cannot mark this request as complete because it is not currently processing."
                )
            )

        vals = {
            "state": "completed",
            "completed_at": fields.Datetime.now(),
        }

        if output_message_id:
            vals["output_message_id"] = output_message_id

        self.write(vals)

    def action_fail(self, error_message=None):
        """Mark job as failed"""
        self.ensure_one()
        if self.state not in ["queued", "running"]:
            raise UserError(
                _(
                    "Cannot mark this request as failed because it has already finished processing."
                )
            )

        vals = {
            "state": "failed",
            "completed_at": fields.Datetime.now(),
        }

        if error_message:
            vals["error_message"] = error_message

        self.write(vals)

    def check_status(self):
        """Check job status with provider"""
        self.ensure_one()
        if self.state != "running" or not self.external_job_id:
            return False

        try:
            status = self.provider_id.check_generation_job_status(self)
            return status
        except Exception as e:
            _logger.error(f"Error checking job {self.id} status: {e}")
            return False

    @api.model
    def cleanup_old_jobs(self, days=7):
        """Clean up completed/failed jobs older than specified days"""
        cutoff_date = fields.Datetime.now() - timedelta(days=days)
        old_jobs = self.search(
            [
                ("state", "in", ["completed", "failed", "cancelled"]),
                ("create_date", "<", cutoff_date),
            ]
        )

        count = len(old_jobs)
        old_jobs.unlink()

        _logger.info(f"Cleaned up {count} old generation jobs")
        return count

    def action_open_thread(self):
        """Open the related thread"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Thread",
            "res_model": "llm.thread",
            "res_id": self.thread_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def _get_generation_context(self):
        """Get context for generation process"""
        self.ensure_one()

        context = {
            "job_id": self.id,
            "thread_id": self.thread_id.id,
            "provider_id": self.provider_id.id,
            "model_id": self.model_id.id,
            "user_id": self.user_id.id,
            "company_id": self.company_id.id,
        }

        if self.generation_inputs:
            context.update(self.generation_inputs)

        return context

    def get_prepared_inputs(self):
        """Get generation inputs prepared with context and templates

        This method is called at job execution time (not creation time) to ensure:
        1. Fresh context is used (important for retries)
        2. Template rendering happens with current data
        3. No serialization issues when storing jobs in the database

        The job stores raw inputs from the user message, and this method
        prepares them just before sending to the provider, matching the
        synchronous generation flow.

        Returns:
            dict: Prepared inputs ready for generation
        """
        self.ensure_one()

        # Check if thread has prepare_generation_inputs method (from llm_generate module)
        if hasattr(self.thread_id, "prepare_generation_inputs"):
            # Get attachment_ids from the input message if available
            attachment_ids = None
            if self.input_message_id and hasattr(
                self.input_message_id, "attachment_ids"
            ):
                attachment_ids = self.input_message_id.attachment_ids

            # Use the thread's method to prepare inputs with context and templates
            # This merges context, renders templates, and returns a dict
            return self.thread_id.prepare_generation_inputs(
                self.generation_inputs or {}, attachment_ids=attachment_ids
            )
        else:
            # Fallback to raw inputs if llm_generate module not installed
            return self.generation_inputs or {}
