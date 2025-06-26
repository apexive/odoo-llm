import json
import logging

from odoo import api, models

from odoo.addons.llm_prompt.utils import render_template

_logger = logging.getLogger(__name__)


class LLMThread(models.Model):
    _inherit = "llm.thread"

    def get_input_schema(self):
        """Get input schema for media generation forms.
        
        Priority:
        1. Thread's prompt input schema
        2. Model's input schema
        
        Returns:
            dict: Input schema for form generation
        """
        self.ensure_one()
        
        schema = {}
        
        # Priority 1: Thread's prompt schema
        if self.prompt_id and hasattr(self.prompt_id, 'input_schema_json') and self.prompt_id.input_schema_json:
            raw_schema = self.prompt_id.input_schema_json
            schema = self._ensure_dict(raw_schema)
            
        # Priority 2: Model's schema  
        elif self.model_id and self.model_id.input_schema:
            raw_schema = self.model_id.input_schema
            schema = self._ensure_dict(raw_schema)
            
        return schema
        
    def _ensure_dict(self, value):
        """Ensure the value is a dictionary.
        
        If the value is a string, try to parse it as JSON.
        
        Args:
            value: The value to convert
            
        Returns:
            dict: The value as a dictionary
        """
        if isinstance(value, dict):
            return value
            
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError as e:
                _logger.error("Failed to parse JSON string: %s", e)
                
        return {}

    def get_form_defaults(self):
        """Get default values for media generation form.
        
        Uses existing get_context() method which includes assistant defaults.
        
        Returns:
            dict: Default values for form fields
        """
        self.ensure_one()

        # Use existing get_context which already handles assistant defaults
        context = self.get_context()

        # Filter context to only include relevant form fields
        schema = self.get_input_schema()
        if not schema or not isinstance(schema, dict) or 'properties' not in schema:
            return context

        # Only return context values that match schema properties
        form_defaults = {}
        schema_properties = schema.get('properties', {})

        for field_name in schema_properties.keys():
            if field_name in context and context[field_name] is not None:
                form_defaults[field_name] = context[field_name]

        return form_defaults

    def prepare_generation_inputs(self, generation_inputs):
        """Prepare final inputs for media generation.

        Args:
            generation_inputs (dict): Raw inputs from form

        Returns:
            dict or str: Final inputs ready for model generation
        """
        self.ensure_one()

        # Get defaults from context (includes assistant defaults)
        defaults = self.get_context()

        # Merge defaults with generation inputs (generation_inputs take precedence)
        merged_context = {**defaults, **generation_inputs}

        # If no prompt, send generation_inputs directly to model
        if not self.prompt_id:
            return merged_context

        # Render the prompt with merged context
        if self.prompt_id:
            try:
                return json.loads(render_template(template=self.prompt_id.template, context=merged_context))

            except Exception as e:
                _logger.error(f"Error rendering prompt: {e}")
                # Fallback to merged inputs if rendering fails
                return merged_context
        else:
            # Fallback: return merged inputs if render_prompt not available
            return merged_context

    def _next_step(self, user_message):
        """Override _next_step to handle media generation messages.
        
        Args:
            user_message: The user message record
            
        Yields:
            dict: Stream events for UI updates
        """
        self.ensure_one()

        # Check if this is a media generation message
        if hasattr(user_message, 'generation_inputs') and user_message.generation_inputs:
            # Parse generation inputs from message
            generation_inputs = json.loads(user_message.generation_inputs)

            # Prepare final inputs using prompt rendering or direct pass-through
            final_inputs = self.prepare_generation_inputs(generation_inputs)
            # Generate media using model
            if self.model_id._is_media_generation_model():
                return self._generate_media_stream(final_inputs)
        # Fall back to parent implementation for regular messages
        return super()._next_step(user_message)

    def _generate_media_stream(self, inputs):
        """Generate media with streaming response.
        
        Args:
            inputs: Final processed inputs for model
            
        Yields:
            dict: Stream events for UI updates
        """
        self.ensure_one()

        try:
            # Generate media using model's generate_media method with streaming
            stream = self.model_id.generate_media(inputs, stream=True)

            # Create message from stream (uses existing method from mail_message.py)
            message_stream = self.env['mail.message'].create_message_from_media_gen_stream(
                thread=self,
                stream=stream,
                subtype_xmlid='llm_mail_message_subtypes.mt_llm_assistant'
            )

            # Yield events from message creation stream
            yield from message_stream

        except Exception as e:
            _logger.error(f"Error in media generation stream: {e}")
            yield {
                'type': 'error',
                'error': f'Media generation failed: {str(e)}'
            }

    @api.model
    def get_model_generation_io_by_id(self, model_id):
        """Get model generation input/output schema by model ID.
        
        Args:
            model_id (int): ID of the llm.model
            
        Returns:
            dict: Model schema information
        """
        try:
            model = self.env['llm.model'].browse(int(model_id))
            if not model.exists():
                raise ValueError(f"Model {model_id} not found")

            return {
                "input_schema": model.input_schema,
                "output_schema": model.output_schema,
                "model_id": model.id,
                "model_name": model.name,
                "model_use": model.model_use,
                "is_media_generation": model._is_media_generation_model(),
            }
        except Exception as e:
            _logger.error(f"Error getting model schema for {model_id}: {e}")
            return {
                "error": str(e),
                "input_schema": None,
                "output_schema": None,
                "model_id": None,
                "model_name": None,
            }

    # @saiful... why...? not dry....
    @api.model
    def build_update_vals(
            self,
            subtype_xmlid,
            tool_call_id=None,
            tool_calls=None,
            tool_call_definition=None,
            tool_call_result=None,
            **kwargs,
    ):
        base_vals = super().build_update_vals(
            subtype_xmlid,
            tool_call_id=tool_call_id,
            tool_calls=tool_calls,
            tool_call_definition=tool_call_definition,
            tool_call_result=tool_call_result,
        )
        if base_vals:
            return base_vals
        generation_inputs = kwargs.get("generation_inputs")
        attachment_ids = kwargs.get("attachment_ids")
        vals = {
            "generation_inputs": generation_inputs,
            "attachment_ids": attachment_ids,
        }
        return {k: v for k, v in vals.items() if v is not None}
