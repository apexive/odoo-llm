import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class LLMThread(models.Model):
    _inherit = "llm.thread"

    # Transcription job relationships
    transcription_job_ids = fields.One2many(
        "llm.transcription.job",
        "thread_id",
        string="Transcription Jobs",
        help="All transcription jobs for this thread",
    )

    # Transcription status
    is_transcribing = fields.Boolean(
        string="Is Transcribing",
        compute="_compute_is_transcribing",
        store=True,
        help="True if thread has active transcription jobs",
    )

    current_transcription_job_id = fields.Many2one(
        "llm.transcription.job",
        string="Current Transcription Job",
        compute="_compute_current_transcription_job",
        help="Current active transcription job",
    )

    # Transcription statistics
    total_transcription_jobs = fields.Integer(
        string="Total Transcription Jobs",
        compute="_compute_transcription_stats",
        help="Total number of transcription jobs",
    )

    successful_transcription_jobs = fields.Integer(
        string="Successful Transcriptions",
        compute="_compute_transcription_stats",
        help="Number of successful transcription jobs",
    )

    failed_transcription_jobs = fields.Integer(
        string="Failed Transcriptions",
        compute="_compute_transcription_stats",
        help="Number of failed transcription jobs",
    )

    transcription_success_rate = fields.Float(
        string="Transcription Success Rate (%)",
        compute="_compute_transcription_stats",
        help="Transcription success rate percentage",
    )

    last_transcription_job_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("queued", "Queued"),
            ("running", "Running"),
            ("completed", "Completed"),
            ("failed", "Failed"),
            ("cancelled", "Cancelled"),
        ],
        string="Last Transcription Job State",
        compute="_compute_last_transcription_job_state",
        help="State of the most recent transcription job",
    )

    @api.depends("transcription_job_ids.state")
    def _compute_is_transcribing(self):
        for thread in self:
            thread.is_transcribing = bool(
                thread.transcription_job_ids.filtered(
                    lambda j: j.state in ["queued", "running"]
                )
            )

    @api.depends("transcription_job_ids.state")
    def _compute_current_transcription_job(self):
        for thread in self:
            active_jobs = thread.transcription_job_ids.filtered(
                lambda j: j.state in ["queued", "running"]
            )
            thread.current_transcription_job_id = active_jobs[:1] if active_jobs else False

    @api.depends("transcription_job_ids.state")
    def _compute_transcription_stats(self):
        for thread in self:
            jobs = thread.transcription_job_ids
            thread.total_transcription_jobs = len(jobs)
            thread.successful_transcription_jobs = len(
                jobs.filtered(lambda j: j.state == "completed")
            )
            thread.failed_transcription_jobs = len(
                jobs.filtered(lambda j: j.state == "failed")
            )

            if thread.total_transcription_jobs > 0:
                thread.transcription_success_rate = (
                    thread.successful_transcription_jobs / thread.total_transcription_jobs
                ) * 100
            else:
                thread.transcription_success_rate = 0.0

    @api.depends("transcription_job_ids.state")
    def _compute_last_transcription_job_state(self):
        for thread in self:
            last_job = thread.transcription_job_ids.sorted("create_date", reverse=True)[:1]
            thread.last_transcription_job_state = last_job.state if last_job else False

    def _transcribe_response(self, last_message):
        """Transcribe with queue support when a queue is configured for the model."""
        self.ensure_one()

        if self.is_transcribing:
            raise UserError(
                _(
                    "A transcription is already running. Please wait for it to complete, "
                    "or cancel the current transcription first."
                )
            )

        queue = (
            self.env["llm.transcription.queue"]
            .sudo()
            .search(
                [("model_id", "=", self.model_id.id), ("enabled", "=", True)], limit=1
            )
        )
        if queue:
            yield from self._transcribe_with_queue_from_message(last_message)
            return

        yield from self._transcribe_direct(last_message)

    def _transcribe_direct(self, last_message):
        """Run synchronous transcription through the direct llm_transcribe flow."""
        self.ensure_one()
        yield from super()._transcribe_response(last_message)

    def _transcribe_with_queue_from_message(self, last_message):
        """Create and monitor a queued transcription job from an existing message."""
        self.ensure_one()

        job = self._create_transcription_job_from_message(last_message)
        self.env.cr.commit()
        job.action_queue()
        yield from self._monitor_transcription_job(job)

    def _create_transcription_job_from_message(self, last_message):
        """Create a transcription job record from an existing message

        Important: This method stores RAW inputs from the message, not prepared inputs.
        The inputs are prepared at job execution time (in the provider) to ensure:
        1. Fresh context is used for each execution (important for retries)
        2. Template rendering uses current data, not stale data from job creation
        3. No JSON serialization issues with non-serializable objects (like RelatedRecordProxy)

        This matches the synchronous flow where prepare_transcription_inputs is called
        just before sending to the model, not when storing the message.
        """
        self.ensure_one()

        # Store raw inputs from message body_json in the job
        transcription_inputs = last_message.body_json or {}

        # Include attachment_ids in the inputs if available
        if hasattr(last_message, "attachment_ids") and last_message.attachment_ids:
            transcription_inputs["attachment_ids"] = last_message.attachment_ids.ids

        # Create job record with raw inputs
        job = (
            self.env["llm.transcription.job"]
            .sudo()
            .create(
                {
                    "thread_id": self.id,
                    "provider_id": self.provider_id.id,
                    "model_id": self.model_id.id,
                    "input_message_id": last_message.id,
                    "transcription_inputs": transcription_inputs,
                    "state": "draft",
                    "user_id": self.env.user.id,  # Explicitly set user_id since we're using sudo
                }
            )
        )

        return job

    def _create_transcription_job(self, user_message_body=None, **kwargs):
        """Create a transcription job record (legacy method for backward compatibility)"""
        self.ensure_one()

        # Post user message first if provided
        input_message = None
        if user_message_body:
            input_message = self.message_post(
                body=user_message_body,
                llm_role="user",
                author_id=self.env.user.partner_id.id,
                **kwargs,
            )

        # Prepare transcription inputs
        transcription_inputs = dict(kwargs)
        if user_message_body:
            transcription_inputs["user_message_body"] = user_message_body

        # Create job record
        job = self.env["llm.transcription.job"].create(
            {
                "thread_id": self.id,
                "provider_id": self.provider_id.id,
                "model_id": self.model_id.id,
                "input_message_id": input_message.id if input_message else False,
                "transcription_inputs": transcription_inputs,
                "state": "draft",
            }
        )

        return job

    def _monitor_transcription_job(self, job):
        """Monitor transcription job and yield streaming updates"""
        import time

        while job.state in ["queued", "running"]:
            # Yield status updates
            yield {
                "type": "job_status",
                "job_id": job.id,
                "state": job.state,
                "message": self._get_job_status_message(job),
            }

            # Check for result message updates
            if job.output_message_id:
                yield {
                    "type": "message_update",
                    "message": job.output_message_id.to_store_format(),
                }

            # Wait before next check
            time.sleep(1)  # Polling interval
            job.invalidate_cache()

        # Final status
        if job.state == "completed":
            message_data = None
            if job.output_message_id:
                message_data = job.output_message_id.to_store_format()

            yield {
                "type": "done",
                "job_id": job.id,
                "message": message_data,
            }
        elif job.state == "failed":
            yield {
                "type": "error",
                "error": job.error_message or "Transcription failed",
                "job_id": job.id,
            }
        elif job.state == "cancelled":
            yield {
                "type": "cancelled",
                "job_id": job.id,
                "message": "Transcription was cancelled",
            }

    def _get_job_status_message(self, job):
        """Get user-friendly status message for job"""
        if job.state == "queued":
            queue = self.env["llm.transcription.queue"].search(
                [("model_id", "=", job.model_id.id)], limit=1
            )

            if queue:
                position = (
                    self.env["llm.transcription.job"].search_count(
                        [
                            ("model_id", "=", job.model_id.id),
                            ("state", "=", "queued"),
                            ("queued_at", "<", job.queued_at),
                        ]
                    )
                    + 1
                )

                return f"Queued (position {position})"
            else:
                return "Queued"
        elif job.state == "running":
            return "Transcribing audio..."
        else:
            return job.state.title()

    def action_cancel_transcription(self):
        """Cancel current transcription job"""
        self.ensure_one()

        if not self.is_transcribing:
            raise UserError(
                _(
                    "There is no transcription in progress to cancel. "
                    "The AI may have already finished responding."
                )
            )

        current_job = self.current_transcription_job_id
        if current_job:
            current_job.action_cancel()
            return True

        return False

    def action_retry_last_failed_transcription(self):
        """Retry the last failed transcription job"""
        self.ensure_one()

        failed_job = self.transcription_job_ids.filtered(
            lambda j: j.state == "failed"
        ).sorted("create_date", reverse=True)[:1]

        if not failed_job:
            raise UserError(
                _(
                    "There are no failed responses to retry. All previous requests completed successfully."
                )
            )

        if failed_job.can_retry:
            failed_job.action_retry()
            return True
        else:
            raise UserError(
                _(
                    "This failed request cannot be retried because it has exceeded the maximum retry limit. "
                    "Please send a new message instead."
                )
            )

    def get_transcription_history(self):
        """Get transcription history for this thread"""
        self.ensure_one()

        jobs = self.transcription_job_ids.sorted("create_date", reverse=True)

        history = []
        for job in jobs:
            history.append(
                {
                    "id": job.id,
                    "state": job.state,
                    "created_at": job.create_date,
                    "queued_at": job.queued_at,
                    "started_at": job.started_at,
                    "completed_at": job.completed_at,
                    "duration": job.duration,
                    "queue_duration": job.queue_duration,
                    "retry_count": job.retry_count,
                    "error_message": job.error_message,
                    "input_message_id": job.input_message_id.id
                    if job.input_message_id
                    else None,
                    "output_message_id": job.output_message_id.id
                    if job.output_message_id
                    else None,
                }
            )

        return history

    def get_transcription_stats(self):
        """Get comprehensive transcription statistics"""
        self.ensure_one()

        return {
            "total_jobs": self.total_transcription_jobs,
            "successful_jobs": self.successful_transcription_jobs,
            "failed_jobs": self.failed_transcription_jobs,
            "success_rate": self.transcription_success_rate,
            "is_transcribing": self.is_transcribing,
            "current_job_id": self.current_transcription_job_id.id
            if self.current_transcription_job_id
            else None,
        }
