import logging

from odoo import models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class LLMProvider(models.Model):
    _inherit = "llm.provider"

    def create_transcription_job(self, job_record):
        """Create a transcription job with the provider

        Args:
            job_record: llm.transcription.job record

        Returns:
            str: External job ID from provider

        Raises:
            NotImplementedError: If provider doesn't support transcription jobs
            UserError: If job creation fails
        """
        return self._dispatch("create_transcription_job", job_record)

    def check_transcription_job_status(self, job_record):
        """Check the status of a transcription job with the provider

        Args:
            job_record: llm.transcription.job record

        Returns:
            dict: Status information containing:
                - state: 'running', 'completed', 'failed'
                - output_message_id: ID of created message (if completed)
                - error_message: Error details (if failed)
                - provider_data: Additional provider-specific data

        Raises:
            NotImplementedError: If provider doesn't support job status checking
        """
        return self._dispatch("check_transcription_job_status", job_record)

    def cancel_transcription_job(self, job_record):
        """Cancel a transcription job with the provider

        Args:
            job_record: llm.transcription.job record

        Returns:
            bool: True if successfully cancelled

        Raises:
            NotImplementedError: If provider doesn't support job cancellation
        """
        return self._dispatch("cancel_transcription_job", job_record)

    def get_transcription_queue_info(self):
        """Get information about the provider's transcription queue

        Returns:
            dict: Queue information containing:
                - max_concurrent_jobs: Maximum concurrent jobs supported
                - current_queue_size: Current number of jobs in queue
                - estimated_wait_time: Estimated wait time in seconds
                - supports_streaming: Whether provider supports streaming
                - supports_cancellation: Whether provider supports job cancellation
        """
        return self._dispatch("get_transcription_queue_info")

    # Default implementations for providers that don't support transcription jobs
    def _default_create_transcription_job(self, job_record):
        """Default implementation - falls back to direct transcription"""
        _logger.warning(
            f"Provider {self.name} doesn't support transcription jobs, falling back to direct transcription"
        )

        thread = job_record.thread_id
        input_message = job_record.input_message_id
        if not input_message:
            raise UserError("Transcription jobs require an input message.")

        try:
            transcription_stream = thread._transcribe_direct(input_message)

            final_message = None
            for chunk in transcription_stream:
                if chunk.get("type") == "message_create":
                    final_message = chunk.get("message")
                elif chunk.get("type") == "message_update":
                    final_message = chunk.get("message")
                elif chunk.get("type") == "error":
                    raise UserError(chunk.get("error", "Unknown error"))

            # Mark job as completed
            if final_message:
                job_record.action_complete(final_message.get("id"))
            else:
                job_record.action_complete()

            return f"direct_transcription_{job_record.id}"

        except Exception as e:
            _logger.error("Error during direct transcription: %s", e, exc_info=True)
            job_record.action_fail(str(e))
            raise

    def _default_check_transcription_job_status(self, job_record):
        """Default implementation - assumes job is handled directly"""
        # For direct transcription, we don't need to check status
        # as it's handled synchronously
        return {
            "state": job_record.state,
            "output_message_id": job_record.output_message_id.id
            if job_record.output_message_id
            else None,
            "error_message": job_record.error_message,
        }

    def _default_cancel_transcription_job(self, job_record):
        """Default implementation - can't cancel direct transcription"""
        _logger.warning(f"Provider {self.name} doesn't support job cancellation")
        return False

    def _default_get_transcription_queue_info(self):
        """Default implementation - basic queue info"""
        return {
            "max_concurrent_jobs": 1,
            "current_queue_size": 0,
            "estimated_wait_time": 0,
            "supports_streaming": False,
            "supports_cancellation": False,
        }
