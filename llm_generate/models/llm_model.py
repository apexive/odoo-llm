from odoo import api, models


class LLMModel(models.Model):
    """Extension of llm.model to support automatic I/O schema generation for media generation models."""

    _inherit = "llm.model"

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to auto-generate I/O schemas for generation models."""
        records = super().create(vals_list)
        records._auto_generate_io_schema()
        return records

    def write(self, vals):
        """Override write to auto-generate I/O schemas when details or model_use changes."""
        result = super().write(vals)
        if "details" in vals or "model_use" in vals:
            self._auto_generate_io_schema()
        return result

    def _auto_generate_io_schema(self):
        """Auto-generate I/O schemas for eligible generation models.

        This method implements the top-level logic:
        1. Check if model_use is generation/image_generation
        2. Check if provider is eligible (via dispatch)
        3. Trigger schema generation (via dispatch)
        """
        for record in self:
            # Top-level condition: only for generation models
            if record.model_use not in ["generation", "image_generation"]:
                continue

            # Skip if no provider
            if not record.provider_id:
                continue

            # Check if provider should generate schema (dispatches to provider implementation)
            if not record.provider_id.should_generate_io_schema(record):
                continue

            # Trigger schema generation (dispatches to provider implementation)
            record.provider_id.generate_io_schema(record)
