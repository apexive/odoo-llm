import json
import logging

import yaml

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.llm_thread.models.llm_thread import RelatedRecordProxy

from ..utils import render_template

_logger = logging.getLogger(__name__)


class LLMThreadMock(models.TransientModel):
    """
    Mock thread model for testing that inherits from llm.thread
    but doesn't require model_id and provider_id to be set.
    """

    _name = "llm.thread.mock"
    _description = "Mock LLM Thread for Testing"
    _inherit = "llm.thread"

    provider_id = fields.Many2one(
        "llm.provider",
        string="Provider",
        required=False,
    )
    model_id = fields.Many2one(
        "llm.model",
        string="Model",
        required=False,
    )


class LLMPromptTest(models.TransientModel):
    _name = "llm.prompt.test"
    _description = "LLM Prompt Test Wizard"

    prompt_id = fields.Many2one(
        "llm.prompt",
        string="Prompt",
        required=True,
        readonly=True,
    )

    # Context and arguments
    test_context = fields.Text(
        string="Test Context (JSON)",
        help="Context arguments to test the prompt with",
        default=lambda self: self._get_default_context(),
    )

    # Reference field for related record selection - allow all models
    related_record_ref = fields.Reference(
        selection="_get_reference_models",
        string="Related Record",
        help="Select any record to use as context for testing related_record.get_field() functions",
    )

    @api.model
    def _get_reference_models(self):
        """Get list of all available models for reference selection."""
        models = self.env["ir.model"].search(
            [
                ("state", "!=", "manual"),
                ("transient", "=", False),
            ],
            order="name",
        )

        return [(model.model, model.name) for model in models]

    # Results
    rendered_template = fields.Text(
        string="Rendered Template",
        readonly=True,
        help="Template after argument substitution",
    )

    messages_json = fields.Text(
        string="Generated Messages (JSON)",
        readonly=True,
        help="Generated messages in JSON format",
    )

    messages_yaml = fields.Text(
        string="Generated Messages (YAML)",
        readonly=True,
        help="Generated messages in YAML format",
    )

    messages_text = fields.Text(
        string="Generated Messages (Text)",
        readonly=True,
        help="Generated messages in readable text format",
    )

    # Display options
    result_format = fields.Selection(
        [
            ("json", "JSON"),
            ("yaml", "YAML"),
            ("text", "Text"),
        ],
        string="Result Format",
        default="json",
    )

    # Status fields
    has_error = fields.Boolean(
        string="Has Error",
        default=False,
        help="Whether there was an error during evaluation",
    )

    error_message = fields.Text(
        string="Error Message",
        readonly=True,
        help="Error message if evaluation failed",
    )

    # Additional fields for displaying prompt info
    original_template = fields.Text(
        string="Original Template",
        compute="_compute_prompt_info",
        help="Original template content from the prompt",
    )

    arguments_schema = fields.Text(
        string="Arguments Schema",
        compute="_compute_prompt_info",
        help="Arguments schema from the prompt",
    )

    @api.depends("prompt_id")
    def _compute_prompt_info(self):
        """Compute prompt information for display"""
        for wizard in self:
            if wizard.prompt_id:
                wizard.original_template = wizard.prompt_id.template or ""
                wizard.arguments_schema = wizard.prompt_id.arguments_json or "{}"
            else:
                wizard.original_template = ""
                wizard.arguments_schema = "{}"

    def _get_default_context(self):
        """Get default context using prompt's method"""
        prompt_id = self.env.context.get("default_prompt_id")
        if not prompt_id:
            return "{}"

        prompt = self.env["llm.prompt"].browse(prompt_id)
        if not prompt.exists():
            return "{}"

        # Use the prompt's method to get default context
        defaults = prompt.get_default_test_context()
        return json.dumps(defaults, indent=2) if defaults else "{}"

    def _create_mock_thread(self):
        """
        Create a mock thread that inherits from llm.thread but doesn't require
        model_id or provider_id to be set.

        Returns:
            llm.thread.mock: Mock thread with same interface as llm.thread
        """
        related_record_ref = self.related_record_ref
        return (
            self.env["llm.thread.mock"]
            .sudo()
            .create(
                {
                    "name": f"Test Thread for {self.prompt_id.name}",
                    "prompt_id": self.prompt_id.id,
                    "model": related_record_ref._name if related_record_ref else False,
                    "res_id": related_record_ref.id if related_record_ref else False,
                }
            )
        )

    def _populate_context_from_record(self):
        """Populate context using direct field access instead of mock thread"""
        if not self.related_record_ref:
            return

        try:
            _logger.info(
                "Auto-populating context from record: %s (ID: %s)",
                self.related_record_ref,
                self.related_record_ref.id,
            )

            # Parse existing context, preserving user data
            try:
                existing_context = json.loads(self.test_context or "{}")
            except json.JSONDecodeError:
                existing_context = {}

            # Generate sample context directly from the record
            sample_context = self._generate_sample_context_direct(
                self.related_record_ref
            )

            # Merge contexts, preserving existing user data
            for key, value in sample_context.items():
                if key not in existing_context:  # Only add if not already present
                    existing_context[key] = value

            self.test_context = json.dumps(existing_context, indent=2)

            _logger.info("Auto-populated context with %d fields", len(sample_context))

        except Exception:
            _logger.exception("Error auto-populating context from record")

    def _generate_sample_context_direct(self, record):
        """
        Generate sample context data directly from a record without using mock thread.

        Args:
            record: The record to extract sample data from

        Returns:
            dict: Sample context data
        """
        if not record:
            return {}

        context = {}

        # Add record metadata
        context["related_model_name"] = record._name
        context["related_model_id"] = record._name
        context["related_res_id"] = record.id

        # Add some common fields from the record as sample data
        sample_fields = [
            "name",
            "display_name",
            "email",
            "phone",
            "mobile",
            "street",
            "city",
            "country_id",
            "state_id",
            "website",
            "description",
            "notes",
            "comment",
            "reference",
            "code",
        ]

        for field_name in sample_fields:
            field_key = f"record_{field_name}"
            if hasattr(record, field_name):
                try:
                    value = getattr(record, field_name)
                    if value:
                        # Handle different field types
                        if hasattr(value, "name"):  # Many2one field
                            context[field_key] = value.name
                        elif hasattr(value, "ids"):  # Many2many/One2many field
                            names = [r.name for r in value[:3]]  # Limit to 3
                            if names:
                                context[field_key] = names
                        else:
                            context[field_key] = str(value)
                except Exception as e:
                    _logger.debug("Could not get field %s: %s", field_name, str(e))
                    continue

        # Add a help note
        context["_related_record_help"] = (
            "Use {{ related_record.get_field('field_name') }} in your template to access record fields directly"
        )

        return context

    def test_prompt_with_context(self, user_context=None):
        """
        Test the prompt with given parameters using mock thread's get_context method.

        Args:
            user_context (dict): Additional context from user (optional)

        Returns:
            dict: Result containing rendered_template, messages, and any errors
        """
        if not self.prompt_id:
            return {
                "success": False,
                "rendered_template": "",
                "messages": [],
                "context_used": {},
                "error": "No prompt configured",
            }

        try:
            # Create a mock thread that inherits from llm.thread
            mock_thread = self._create_mock_thread()

            try:
                # Get context using the mock thread's canonical get_context method
                context = mock_thread.get_context(user_context)

                # Mark as test to avoid updating usage statistics
                context["is_test"] = True

                # Use the prompt to render and generate messages (same as production)
                rendered_template = render_template(
                    template=self.prompt_id.template, context=context
                )
                messages = self.prompt_id.get_messages(context)

                return {
                    "success": True,
                    "rendered_template": rendered_template,
                    "messages": messages,
                    "context_used": context,
                    "error": None,
                }
            finally:
                # Clean up mock thread (it's transient so will be cleaned up automatically)
                mock_thread.unlink()

        except Exception as e:
            _logger.exception("Error testing prompt %s", self.prompt_id.name)
            return {
                "success": False,
                "rendered_template": "",
                "messages": [],
                "context_used": user_context or {},
                "error": str(e),
            }

    @api.onchange("related_record_ref")
    def _onchange_related_record_ref(self):
        """Auto-populate context and evaluate when record is selected"""
        # Store the current value to prevent it from being cleared
        current_record = self.related_record_ref

        if current_record:
            # Auto-populate context with record data
            self._populate_context_from_record()
            # Auto-evaluate the prompt
            self._auto_evaluate_prompt()
            # Ensure the record reference is preserved
            self.related_record_ref = current_record
        else:
            # Clear related record metadata from context when record is cleared
            try:
                context = json.loads(self.test_context or "{}")
                # Remove related record metadata
                context.pop("related_model_name", None)
                context.pop("related_model_id", None)
                context.pop("related_res_id", None)
                context.pop("_related_record_help", None)
                # Remove all record_* fields
                context = {
                    k: v for k, v in context.items() if not k.startswith("record_")
                }
                self.test_context = json.dumps(context, indent=2)
            except (json.JSONDecodeError, Exception):
                pass

    def _auto_evaluate_prompt(self):
        """Auto-evaluate prompt with minimal mock thread usage"""
        try:
            # Parse test context
            try:
                user_context = json.loads(self.test_context or "{}")
            except json.JSONDecodeError:
                return  # Skip if invalid JSON

            # For auto-evaluation, use a lighter approach to avoid reference field issues
            result = self._test_prompt_light(user_context)

            # Update wizard fields based on result
            self._update_wizard_from_result(result)

        except Exception as e:
            _logger.debug("Auto-evaluation failed: %s", str(e))
            self.has_error = True
            self.error_message = f"Auto-evaluation error: {str(e)}"

    def _test_prompt_light(self, user_context=None):
        """
        Lightweight test of the prompt that avoids creating mock threads during onchange.
        Used for auto-evaluation to prevent reference field clearing.

        Args:
            user_context (dict): Additional context from user (optional)

        Returns:
            dict: Result containing rendered_template, messages, and any errors
        """
        if not self.prompt_id:
            return {
                "success": False,
                "rendered_template": "",
                "messages": [],
                "context_used": {},
                "error": "No prompt configured",
            }

        try:
            # Build context directly without mock thread
            context = dict(user_context or {})

            # Add thread-specific context manually
            context["thread_id"] = "test"
            context["is_test"] = True

            # Add related_record proxy if we have a record
            if self.related_record_ref:
                context["related_record"] = RelatedRecordProxy(self.related_record_ref)
                context["related_model_name"] = self.related_record_ref._name
                context["related_model_id"] = self.related_record_ref._name
                context["related_res_id"] = self.related_record_ref.id
            else:
                context["related_record"] = RelatedRecordProxy(None)
                context["related_model_name"] = None
                context["related_model_id"] = None
                context["related_res_id"] = None

            # Use the prompt to render and generate messages (same as production)
            rendered_template = render_template(
                template=self.prompt_id.template, context=context
            )
            messages = self.prompt_id.get_messages(context)

            return {
                "success": True,
                "rendered_template": rendered_template,
                "messages": messages,
                "context_used": context,
                "error": None,
            }

        except Exception as e:
            _logger.exception(
                "Error testing prompt %s (light mode)", self.prompt_id.name
            )
            return {
                "success": False,
                "rendered_template": "",
                "messages": [],
                "context_used": user_context or {},
                "error": str(e),
            }

    def _update_wizard_from_result(self, result):
        """Update wizard fields from test result"""
        if result["success"]:
            self.has_error = False
            self.error_message = ""
            self.rendered_template = result["rendered_template"]

            # Convert messages to different formats
            messages = result["messages"]
            self.messages_json = json.dumps(messages, indent=2, ensure_ascii=False)

            # Convert to YAML
            try:
                self.messages_yaml = yaml.dump(
                    messages, default_flow_style=False, allow_unicode=True, indent=2
                )
            except Exception as e:
                self.messages_yaml = f"Error converting to YAML: {str(e)}"

            # Convert to readable text
            self.messages_text = self._format_messages_as_text(messages)
        else:
            self.has_error = True
            self.error_message = result["error"]
            self.rendered_template = ""
            self.messages_json = ""
            self.messages_yaml = ""
            self.messages_text = f"Error during evaluation: {result['error']}"

    def _format_messages_as_text(self, messages):
        """Format messages as readable text"""
        text_parts = []
        for i, message in enumerate(messages, 1):
            role = message.get("role", "unknown")
            content = message.get("content", "")

            # Extract text content
            if isinstance(content, list) and len(content) > 0:
                text_content = content[0].get("text", "")
            elif isinstance(content, str):
                text_content = content
            else:
                text_content = str(content)

            text_parts.append(f"Message {i} ({role.upper()}):\n{text_content}\n")

        return "\n" + "=" * 50 + "\n".join(text_parts)

    def action_evaluate_prompt(self):
        """Evaluate the prompt using mock thread's test method"""
        self.ensure_one()

        if not self.prompt_id:
            raise ValidationError(_("Please select a prompt template before testing."))

        try:
            # Parse test context
            try:
                user_context = json.loads(self.test_context or "{}")
            except json.JSONDecodeError as e:
                raise ValidationError(
                    _(
                        "The test context contains invalid JSON. Please check the format "
                        "and ensure all brackets and quotes are properly matched.\n\n"
                        "Details: %s"
                    )
                    % str(e)
                ) from e

            # Use our test method - this uses mock thread's get_context
            result = self.test_prompt_with_context(user_context)

            # Update wizard fields based on result
            self._update_wizard_from_result(result)

        except ValidationError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            self.has_error = True
            self.error_message = str(e)
            self.rendered_template = ""
            self.messages_json = ""
            self.messages_yaml = ""
            self.messages_text = f"Error during evaluation: {str(e)}"
            _logger.exception("Error evaluating prompt %s", self.prompt_id.name)

        # Return an action to keep the wizard open and preserve context
        return {
            "type": "ir.actions.act_window",
            "res_model": "llm.prompt.test",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "context": dict(self.env.context, keep_context=True),
        }

    def action_reset_context(self):
        """Reset context to defaults using prompt's method"""
        self.ensure_one()
        self.test_context = self._get_default_context()
        self.related_record_ref = False

        # Clear results
        self.rendered_template = ""
        self.messages_json = ""
        self.messages_yaml = ""
        self.messages_text = ""
        self.has_error = False
        self.error_message = ""

        return {
            "type": "ir.actions.act_window",
            "res_model": "llm.prompt.test",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "context": dict(self.env.context, keep_context=True),
        }

    def action_clear_related_record(self):
        """Clear the related record selection"""
        self.ensure_one()
        self.related_record_ref = False

        return {
            "type": "ir.actions.act_window",
            "res_model": "llm.prompt.test",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "context": dict(self.env.context, keep_context=True),
        }

    def action_populate_with_defaults(self):
        """Populate context with prompt's default values"""
        self.ensure_one()

        if self.prompt_id:
            defaults = self.prompt_id.get_default_test_context()

            # Merge with existing context
            try:
                existing_context = json.loads(self.test_context or "{}")
            except json.JSONDecodeError:
                existing_context = {}

            # Add defaults for missing keys
            for key, value in defaults.items():
                if key not in existing_context:
                    existing_context[key] = value

            self.test_context = json.dumps(existing_context, indent=2)

            # Auto-evaluate after populating
            self._auto_evaluate_prompt()

        return {
            "type": "ir.actions.act_window",
            "res_model": "llm.prompt.test",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "context": dict(self.env.context, keep_context=True),
        }

    def action_format_context(self):
        """Format the context JSON for better readability"""
        self.ensure_one()

        try:
            context = json.loads(self.test_context or "{}")
            self.test_context = json.dumps(context, indent=2, sort_keys=True)
        except json.JSONDecodeError:
            # If invalid JSON, try to fix common issues
            try:
                # Remove trailing commas and other common issues
                fixed_json = self.test_context.strip()
                if fixed_json.endswith(","):
                    fixed_json = fixed_json[:-1]
                context = json.loads(fixed_json)
                self.test_context = json.dumps(context, indent=2, sort_keys=True)
            except Exception:
                pass  # Keep original if we can't fix it

        return {
            "type": "ir.actions.act_window",
            "res_model": "llm.prompt.test",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "context": dict(self.env.context, keep_context=True),
        }
