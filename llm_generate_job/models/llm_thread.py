import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class LLMThread(models.Model):
    _inherit = "llm.thread"

    # Relationship to generation jobs
    generation_job_ids = fields.One2many(
        'llm.generate.job',
        'thread_id',
        string='Generation Jobs',
        help='Generation jobs associated with this thread'
    )

    # Count of active jobs
    active_job_count = fields.Integer(
        string='Active Jobs',
        compute='_compute_active_job_count',
        help='Number of active generation jobs for this thread'
    )

    @api.depends('generation_job_ids.state')
    def _compute_active_job_count(self):
        for record in self:
            record.active_job_count = len(record.generation_job_ids.filtered(
                lambda j: j.state in ['draft', 'submitted', 'queued', 'processing']
            ))

    def create_generation_job(self, generation_inputs, model_id=None, name=None):
        """Create a new generation job for this thread"""
        self.ensure_one()
        
        # Use thread's model if not specified
        if not model_id:
            model_id = self.model_id.id
        
        # Generate name if not provided
        if not name:
            name = f"Generation Job - {self.name}"
        
        job_vals = {
            'name': name,
            'provider_id': self.provider_id.id,
            'model_id': model_id,
            'thread_id': self.id,
            'generation_inputs': generation_inputs,        }
        
        return self.env['llm.generate.job'].create(job_vals)

    def submit_async_generation(self, generation_inputs):
        """Submit an async generation job and return job ID"""
        self.ensure_one()

        # Check if provider supports async generation
        if not self.provider_id.supports_async_generation():
            raise ValueError(f"Provider {self.provider_id.name} does not support async generation")

        # Create and optionally submit job
        job = self.create_generation_job(generation_inputs)
        job.action_submit()
            # Post notification to thread
        self.message_post(
                body=f"🚀 **Generation job submitted**\n\nJob ID: {job.id}\nStatus: {job.state}\n\nYou will be notified when the generation is complete.",
                subtype_xmlid='llm_mail_message_subtypes.llm_assistant'
        )

        return job

    def get_pending_jobs(self):
        """Get all pending generation jobs for this thread"""
        self.ensure_one()
        return self.generation_job_ids.filtered(
            lambda j: j.state in ['draft', 'submitted', 'queued', 'processing']
        )

    def cancel_all_pending_jobs(self):
        """Cancel all pending generation jobs for this thread"""
        self.ensure_one()
        pending_jobs = self.get_pending_jobs()
        
        for job in pending_jobs:
            try:
                job.action_cancel()
            except Exception as e:
                _logger.warning(f"Failed to cancel job {job.id}: {e}")
        
        return len(pending_jobs)

    def check_async_generation_support(self):
        """Verifica si el proveedor de este thread soporta generación asíncrona"""
        self.ensure_one()

        if not self.provider_id:
            return {"supports_async": False, "error": "No provider found for this thread"}

        # Verificar soporte de generación asíncrona
        supports_async = self.provider_id.supports_async_generation()

        return {
            "supports_async": supports_async,
            "provider_name": self.provider_id.name,
            "provider_id": self.provider_id.id
        }
