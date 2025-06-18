import logging

from odoo import api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class LLMProvider(models.Model):
    _inherit = "llm.provider"

    def is_webhook(self, request):
        """Check if the request is a webhook call"""
        return False

    def verify_webhook(self, request, webhook_data):
        """Verify the webhook data from the request"""
        raise False

    def supports_async_generation(self):
        """Check if this provider supports async generation"""
        return self._dispatch("supports_async_generation")

    def submit_generation_job(self, job_record):
        """Submit a generation job with webhook support"""
        return self._dispatch("submit_generation_job", job_record)

    def check_generation_job_status(self, job_record):
        """Check the status of a generation job with the provider"""
        return self._dispatch("check_generation_job_status", job_record)

    def cancel_generation_job(self, external_job_id):
        """Cancel a generation job with the provider"""
        return self._dispatch("cancel_generation_job", external_job_id)

    def _dispatch(self, method_name, *args, **kwargs):
        """Dispatch method calls to provider-specific implementations"""
        method = getattr(self, f"{self.service}_{method_name}", None)
        if method:
            return method(*args, **kwargs)
        else:
            # Check if there's a default implementation
            default_method = getattr(self, f"default_{method_name}", None)
            if default_method:
                return default_method(*args, **kwargs)
            raise UserError(f"Method {method_name} not implemented for provider {self.service}")

    # Default implementations that can be overridden by specific providers

    def default_supports_async_generation(self):
        """Default implementation - most providers don't support async generation"""
        return False

    def default_submit_generation_job(self, job_record):
        """Default implementation for job submission"""
        raise UserError(f"Generation job submission not implemented for provider {self.name}")

    def default_check_generation_job_status(self, job_record):
        """Default implementation for status checking"""
        raise UserError(f"Generation job status checking not implemented for provider {self.name}")

    def default_cancel_generation_job(self, external_job_id):
        """Default implementation for job cancellation"""
        raise UserError(f"Generation job cancellation not implemented for provider {self.name}")
