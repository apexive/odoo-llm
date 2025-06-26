from odoo import api, fields, models


class LLMModel(models.Model):
    _inherit = "llm.model"

    input_schema = fields.Json(
        string="Input Schema",
        help="JSON Schema defining the input parameters for this generation task",
        store=True,
    )
    output_schema = fields.Json(
        string="Output Schema",
        help="JSON Schema defining the output parameters for this generation task",
        store=True,
    )

    @api.model
    def _get_available_model_usages(self):
        available_usages = super()._get_available_model_usages()
        return available_usages + [
            ("image_generation", "Image Generation"),
        ]

    def _is_media_generation_model(self):
        """Helper to check if model_use indicates a non-chat/embedding generative task."""
        self.ensure_one()
        return self.model_use in ["image_generation"]

    @api.depends("details", "model_use", "name", "provider_id")
    def _compute_io_schema(self):
        """Compute input and output schemas based on model details and usage"""
        for record in self:
            if record._is_media_generation_model() and record.provider_id:
                # Trigger provider-specific schema generation
                record.provider_id.generate_io_schema(model_record=record)

    def generate_media(self, inputs, stream=False):
        """Generate content using this model with the specified inputs.

        Args:
            inputs (dict): The input parameters for generation according to the schema

        Returns:
            The generated content (format depends on the model type and configuration)
        """
        self.ensure_one()

        # Validate model is configured for generation
        if not self._is_media_generation_model():
            raise ValueError(
                f"Model {self.name} is not configured for generation tasks"
            )

        # Dispatch to provider-specific implementation
        return self.provider_id._dispatch(
            "generate_media", inputs=inputs, model_record=self, stream=stream
        )

    def format_generation_response(self, raw_response):
        """Format the raw generation response according to the output processing config

        Args:
            raw_response: The raw response from the provider

        Returns:
            Processed response in the format specified by the config
        """
        self.ensure_one()

        # Dispatch to provider-specific implementation
        return self.provider_id._dispatch(
            "format_generation_response",
            raw_response=raw_response,
            output_schema=self.output_schema,
        )

    @api.model
    def get_model_gen_io_by_id(self, model_id):
        model = self.browse(int(model_id))
        if not model.exists():
            raise ValueError(f"Model {model_id} not found")

        return {
            "input_schema": model.input_schema,
            "output_schema": model.output_schema,
            "model_id": model.id,
            "model_name": model.name,
        }
