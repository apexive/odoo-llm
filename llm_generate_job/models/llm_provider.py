import logging

from odoo import models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class LLMProvider(models.Model):
    _inherit = "llm.provider"

    def create_generation_job(self, job_record):
        """Create a generation job with the provider

        Args:
            job_record: llm.generation.job record

        Returns:
            str: External job ID from provider

        Raises:
            NotImplementedError: If provider doesn't support generation jobs
            UserError: If job creation fails
        """
        return self._dispatch("create_generation_job", job_record)

    def check_generation_job_status(self, job_record):
        """Check the status of a generation job with the provider

        Args:
            job_record: llm.generation.job record

        Returns:
            dict: Status information containing:
                - state: 'running', 'completed', 'failed'
                - output_message_id: ID of created message (if completed)
                - error_message: Error details (if failed)
                - provider_data: Additional provider-specific data

        Raises:
            NotImplementedError: If provider doesn't support job status checking
        """
        return self._dispatch("check_generation_job_status", job_record)

    def cancel_generation_job(self, job_record):
        """Cancel a generation job with the provider

        Args:
            job_record: llm.generation.job record

        Returns:
            bool: True if successfully cancelled

        Raises:
            NotImplementedError: If provider doesn't support job cancellation
        """
        return self._dispatch("cancel_generation_job", job_record)

    def get_generation_queue_info(self):
        """Get information about the provider's generation queue

        Returns:
            dict: Queue information containing:
                - max_concurrent_jobs: Maximum concurrent jobs supported
                - current_queue_size: Current number of jobs in queue
                - estimated_wait_time: Estimated wait time in seconds
                - supports_streaming: Whether provider supports streaming
                - supports_cancellation: Whether provider supports job cancellation
        """
        return self._dispatch("get_generation_queue_info")

    # Default implementations for providers that don't support generation jobs
    def _default_create_generation_job(self, job_record):
        """Default implementation - falls back to direct generation"""
        _logger.warning(
            f"Provider {self.name} doesn't support generation jobs, falling back to direct generation"
        )

        # Get the thread and trigger direct generation
        thread = job_record.thread_id

        # Get user message body if available
        user_message_body = None
        if job_record.input_message_id:
            user_message_body = job_record.input_message_id.body

        # Use the generation inputs if available
        kwargs = {}
        if job_record.generation_inputs:
            kwargs.update(job_record.generation_inputs)

        # Start direct generation using the original thread method
        try:
            # Use the underlying generation method directly
            generation_stream = thread._generate_direct(user_message_body, **kwargs)

            # Process the stream and get the final message
            final_message = None
            for chunk in generation_stream:
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

            return f"direct_generation_{job_record.id}"

        except Exception as e:
            _logger.error("Error during direct generation: %s", e, exc_info=True)
            job_record.action_fail(str(e))
            raise

    def _default_check_generation_job_status(self, job_record):
        """Default implementation - assumes job is handled directly"""
        # For direct generation, we don't need to check status
        # as it's handled synchronously
        return {
            "state": job_record.state,
            "output_message_id": job_record.output_message_id.id
            if job_record.output_message_id
            else None,
            "error_message": job_record.error_message,
        }

    def _default_cancel_generation_job(self, job_record):
        """Default implementation - can't cancel direct generation"""
        _logger.warning(f"Provider {self.name} doesn't support job cancellation")
        return False

    def _default_get_generation_queue_info(self):
        """Default implementation - basic queue info"""
        return {
            "max_concurrent_jobs": 1,
            "current_queue_size": 0,
            "estimated_wait_time": 0,
            "supports_streaming": True,
            "supports_cancellation": False,
        }
