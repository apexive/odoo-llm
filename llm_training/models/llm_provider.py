from odoo import models


class LLMProvider(models.Model):
    _inherit = "llm.provider"

    def upload_file(self, file_tuple, purpose="fine-tune"):
        """Upload a file to the provider"""
        return self._dispatch("upload_file", file_tuple, purpose)

    def create_training_job(self, training_file_id, model_name, hyperparameters=None):
        """Create a fine-tuning job with the provider."""
        return self._dispatch(
            "create_training_job", training_file_id, model_name, hyperparameters
        )

    def retrieve_training_job(self, job_id):
        """Retrieve a fine-tuning job with the provider."""
        return self._dispatch("retrieve_training_job", job_id)

    def cancel_training_job(self, job_id):
        """Cancel a fine-tuning job with the provider."""
        return self._dispatch("cancel_training_job", job_id)

    def start_training_job(self, job_record):
        """Start a training job full process with the provider."""
        return self._dispatch("start_training_job", job_record)

    def check_training_job_status(self, job_record):
        """Check the status of a training job with the provider."""
        return self._dispatch("check_training_job_status", job_record)

    def validate_datasets(self, job_record):
        """Validate datasets for training"""
        return self._dispatch("validate_datasets", job_record)
