import json
import logging

from odoo import api, models

from odoo.addons.llm_assistant.utils import render_template

_logger = logging.getLogger(__name__)


class LLMThread(models.Model):
    _inherit = "llm.thread"

    def get_input_schema(self):
        """Get input schema for generation forms."""
        self.ensure_one()

        # Priority order:
        # 1. Assistant's prompt schema (if assistant selected)
        # 2. Thread's direct prompt schema (if prompt directly selected)
        # 3. Model's default schema

        # Check assistant's prompt first
        if (
            hasattr(self, "assistant_id")
            and self.assistant_id
            and self.assistant_id.prompt_id
        ):
            prompt_schema = self._ensure_dict(
                self.assistant_id.prompt_id.input_schema_json
            )
            if prompt_schema and prompt_schema.get("properties"):
                return prompt_schema

        # Check thread's direct prompt
        if self.prompt_id and hasattr(self.prompt_id, "input_schema_json"):
            prompt_schema = self._ensure_dict(self.prompt_id.input_schema_json)
            if prompt_schema and prompt_schema.get("properties"):
                return prompt_schema

        # Fall back to model schema
        if self.model_id and self.model_id.details:
            return self._ensure_dict(self.model_id.details.get("input_schema", {}))

        return {}

    def _ensure_dict(self, value):
        """Convert value to dict if it's a JSON string."""
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return {}
        return {}

    def get_form_defaults(self):
        """Get default values for generation form from context."""
        self.ensure_one()
        context = self.get_context()
        schema = self.get_input_schema()

        # Start with context values
        defaults = dict(context)

        # Add schema defaults for any missing properties
        if schema.get("properties"):
            for prop_name, prop_def in schema["properties"].items():
                if prop_name not in defaults and "default" in prop_def:
                    defaults[prop_name] = prop_def["default"]

            # Filter to only include schema properties
            defaults = {
                k: v
                for k, v in defaults.items()
                if k in schema["properties"] and v is not None
            }

        return defaults

    def get_generation_form_config(self):
        """Get form configuration for generation (schema + defaults)

        Wrapper method that combines get_input_schema() and get_form_defaults()
        into a single call for the frontend.
        """
        self.ensure_one()

        return {
            "input_schema": self.get_input_schema(),
            "form_defaults": self.get_form_defaults(),
        }

    def prepare_generation_inputs(self, inputs, attachment_ids=None):
        """Prepare final inputs for generation.

        Args:
            inputs (dict): Raw inputs from form

        Returns:
            dict: Final inputs ready for model generation
        """

        self.ensure_one()

        # Merge context with inputs
        context = self.get_context()
        merged_inputs = {**context, **inputs}

        # If no prompt, return merged inputs
        if not self.prompt_id:
            return merged_inputs

        # Render prompt with merged inputs
        try:
            rendered = render_template(self.prompt_id.template, merged_inputs)
            return json.loads(rendered)
        except Exception as e:
            _logger.error(f"Error rendering prompt: {e}")
            return merged_inputs

    def _generate_response(self, message):
        """Handle a user message with generation data in body_json.

        If anything goes wrong, this method will fail cleanly without
        creating an assistant message or committing the cursor.
        """
        self.ensure_one()

        # Prepare final inputs
        final_inputs = self.prepare_generation_inputs(
            message.body_json or {}, attachment_ids=message.attachment_ids
        )

        _logger.info(final_inputs)
        # Generate using model - now returns tuple (output_data, urls)
        output_data, urls = self.model_id.generate(final_inputs)

        # TODO: CRITICAL - Fix Replicate file expiration (API predictions deleted after 1 hour)
        # Current: URLs stored as type='url' attachments → break after expiry
        # Solution: Implement provider hook pattern for downloading outputs
        #   1. Add provider.download_generation_output(url_data) hook in llm.provider base
        #   2. Implement in llm_replicate to download files before expiry
        #   3. Pass provider_id in url_data dict from generate()
        #   4. Update mail_message._create_url_attachment() to:
        #      - Check if provider has download hook
        #      - Download and create type='binary' attachment with datas field
        #      - Fall back to type='url' for providers that don't need download
        #
        # TODO: Fix misleading variable naming
        # - "output_data" actually contains INPUT metadata (model_name, inputs, provider, num_outputs)
        # - The actual OUTPUT (images/videos) is in "urls" and becomes attachments

        # Create assistant message first (without attachments)
        generated_message = self.message_post(
            body="",  # Will be updated with markdown content
            llm_role="assistant",
            body_json=output_data,  # Misleading name - contains input metadata, not output
        )

        # Use message method to process URLs and create attachments
        markdown_content, attachments = generated_message.process_generation_urls(urls)

        # Update message with final markdown content (process markdown to HTML)
        html_content = self._process_llm_body(markdown_content)
        generated_message.write({"body": html_content})

        # Yield the successful result
        yield {
            "type": "message_create",
            "message": generated_message.to_store_format(),
        }

        # Return the actual message record for yield from compatibility
        return generated_message

    @api.model
    def get_model_generation_io_by_id(self, model_id):
        """Get model generation I/O schema by ID."""
        try:
            model = self.env["llm.model"].browse(int(model_id))
            if not model.exists():
                return {"error": f"Model {model_id} not found"}

            return {
                "input_schema": model.details.get("input_schema")
                if model.details
                else None,
                "output_schema": model.details.get("output_schema")
                if model.details
                else None,
                "model_id": model.id,
                "model_name": model.name,
            }
        except Exception as e:
            return {"error": str(e)}
