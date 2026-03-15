"""Model Tools - LLM tools for inspecting Odoo models and records"""

import logging

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.llm_tool.decorators import llm_tool

_logger = logging.getLogger(__name__)


class IrModel(models.Model):
    """Inherit IR Model to add LLM tools"""

    _inherit = "ir.model"

    @llm_tool(
        schema={
            "type": "object",
            "properties": {
                "model_name": {
                    "type": "string",
                    "description": "Technical name of the Odoo model (e.g., 'res.partner')",
                },
                "record_id": {
                    "type": "integer",
                    "description": "ID of the record to retrieve",
                },
            },
            "required": ["model_name", "record_id"],
        },
        read_only_hint=True,
    )
    def get_record_info(self, model_name, record_id):
        """Get basic information about any Odoo record (legacy example without type hints)

        This demonstrates how to use @llm_tool with existing code that doesn't have
        type hints by providing a manual schema.

        This is useful for:
        - Legacy code that can't be modified
        - Methods with complex parameter types
        - Backward compatibility

        Args:
            model_name: Technical name of the model
            record_id: ID of the record

        Returns:
            Dictionary with record information
        """
        # Validate model exists
        if model_name not in self.env:
            raise UserError(_("Model '%s' does not exist") % model_name)

        # Get the record
        try:
            record = self.env[model_name].browse(record_id)
            if not record.exists():
                raise UserError(
                    _("Record with ID %s not found in model %s")
                    % (record_id, model_name)
                )
        except Exception as e:
            raise UserError(_("Error accessing record: %s") % str(e)) from e

        # Get display name and basic info
        result = {
            "model": model_name,
            "id": record_id,
            "display_name": record.display_name,
        }

        # Add some common fields if they exist
        for field in ["name", "active", "create_date", "write_date"]:
            if field in record._fields:
                value = record[field]
                # Convert to string for JSON serialization
                result[field] = str(value) if value else None

        return result
