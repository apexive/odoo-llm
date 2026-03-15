from odoo import models


class LLMProvider(models.Model):
    """Extension of llm.provider to support I/O schema generation for media generation models."""

    _inherit = "llm.provider"

    def generate_io_schema(self, model_record):
        """Generate input/output schema for a media generation model.

        Dispatches to {service}_generate_io_schema() implementation.
        """
        return self._dispatch("generate_io_schema", model_record)

    def should_generate_io_schema(self, model_record):
        """Check if I/O schema should be generated for the model.

        Dispatches to {service}_should_generate_io_schema() implementation.
        """
        return self._dispatch("should_generate_io_schema", model_record)
