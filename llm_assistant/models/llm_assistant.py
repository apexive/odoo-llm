import json
import logging
import re

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval
from odoo.addons.llm_prompt.utils import render_template

_logger = logging.getLogger(__name__)


class LLMAssistant(models.Model):
    _name = "llm.assistant"
    _description = "LLM Assistant"
    _inherit = ["mail.thread"]
    _order = "name"

    name = fields.Char(
        string="Name",
        required=True,
        tracking=True,
    )
    active = fields.Boolean(default=True, tracking=True)

    # Assistant configuration
    provider_id = fields.Many2one(
        "llm.provider",
        string="Provider",
        ondelete="restrict",
        tracking=True,
    )
    model_id = fields.Many2one(
        "llm.model",
        string="Model",
        domain="[('provider_id', '=', provider_id)]",
        ondelete="restrict",
        tracking=True,
        required=False,
    )
    is_public = fields.Boolean(
        string="Public",
        default=False,
        help="If checked, this assistant will be available to all users",
    )

    allowed_group_ids = fields.Many2many(
        "res.groups",
        "llm_assistant_group_rel",
        "assistant_id",
        "group_id",
        string="Allowed Groups",
        help="Groups that can access this assistant. If empty and not public, only internal users can access it.",
    )

    # Prompt template integration
    prompt_id = fields.Many2one(
        "llm.prompt",
        string="Prompt Template",
        ondelete="restrict",
        tracking=True,
        required=True,
        help="Prompt template to use for generating system prompts",
    )

    # Related fields from prompt - for display and search
    category_id = fields.Many2one(
        "llm.prompt.category",
        string="Category",
        related="prompt_id.category_id",
        store=True,
        readonly=True,
        help="Category inherited from the prompt template",
    )

    tag_ids = fields.Many2many(
        "llm.prompt.tag",
        string="Tags",
        related="prompt_id.tag_ids",
        readonly=True,
        help="Tags inherited from the prompt template",
    )

    # Default values for prompt variables as JSON
    default_values = fields.Text(
        string="Default Values",
        help="JSON object with default values for prompt variables. Can include template expressions that will be evaluated.",
        default="{}",
        tracking=True,
    )

    # Whether default values contain expressions to be evaluated
    has_dynamic_defaults = fields.Boolean(
        string="Has Dynamic Defaults",
        default=False,
        help="Enable if your default values contain template expressions that should be evaluated",
        tracking=True,
    )

    # Tools configuration
    tool_ids = fields.Many2many(
        "llm.tool",
        string="Preferred Tools",
        help="Tools that this assistant can use",
        tracking=True,
    )

    # Stats
    thread_count = fields.Integer(
        string="Thread Count",
        compute="_compute_thread_count",
        help="Number of threads using this assistant",
    )
    thread_ids = fields.One2many(
        "llm.thread",
        "assistant_id",
        string="Threads",
        help="Threads using this assistant",
    )

    system_prompt_preview = fields.Text(
        string="System Prompt Preview",
        compute="_compute_system_prompt_preview",
        help="Preview of the formatted system prompt based on the prompt template",
    )

    # Template fields - computed from prompt
    template = fields.Text(
        string="Template",
        related="prompt_id.template",
        readonly=True,
        help="Template content from the associated prompt",
    )

    template_format = fields.Selection(
        string="Template Format",
        related="prompt_id.format",
        readonly=True,
        help="Format of the template (text, yaml, json)",
    )

    @api.depends("prompt_id", "default_values")
    def _compute_system_prompt_preview(self):
        """Compute preview of the formatted system prompt"""
        for assistant in self:
            try:
                if assistant.prompt_id:
                    # Get evaluated default values for preview
                    default_values = assistant.get_evaluated_default_values({})
                    messages = assistant.prompt_id.get_messages(default_values)
                    if messages:
                        # Find system message or use first message
                        system_msg = next(
                            (msg for msg in messages if msg.get("role") == "system"),
                            messages[0] if messages else None,
                        )
                        if system_msg and system_msg.get("content"):
                            content = system_msg["content"]
                            if isinstance(content, list) and content:
                                assistant.system_prompt_preview = content[0].get(
                                    "text", ""
                                )
                            elif isinstance(content, str):
                                assistant.system_prompt_preview = content
                            else:
                                assistant.system_prompt_preview = str(content)
                        else:
                            assistant.system_prompt_preview = (
                                "No system prompt generated"
                            )
                    else:
                        assistant.system_prompt_preview = "No messages generated"
                else:
                    assistant.system_prompt_preview = "No prompt template selected"
            except Exception as e:
                _logger.error(
                    "Error computing system prompt preview for assistant %s: %s",
                    assistant.name,
                    str(e),
                )
                assistant.system_prompt_preview = f"Error: {str(e)}"

    @api.depends("thread_ids")
    def _compute_thread_count(self):
        """Compute the number of threads using this assistant"""
        for assistant in self:
            assistant.thread_count = len(assistant.thread_ids)

    def action_view_prompt(self):
        """Open the associated prompt for advanced template management"""
        self.ensure_one()
        if not self.prompt_id:
            return False

        return {
            "name": "Prompt Template",
            "type": "ir.actions.act_window",
            "res_model": "llm.prompt",
            "view_mode": "form",
            "res_id": self.prompt_id.id,
            "target": "current",
        }

    def action_view_threads(self):
        """Open the threads using this assistant"""
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "llm_thread.llm_thread_action"
        )
        action["domain"] = [("assistant_id", "=", self.id)]
        action["context"] = {"default_assistant_id": self.id}
        return action

    def _generate_template_json_from_schema(self, args_schema):
        """
        Generate a template JSON structure from the prompt's argument schema.
        Creates placeholders for all arguments, using defaults when available.

        Args:
            args_schema (dict): The arguments schema from the prompt

        Returns:
            dict: Template values with placeholders or defaults
        """
        template_values = {}

        for arg_name, arg_schema in args_schema.items():
            # If there's a default value, use it
            if "default" in arg_schema:
                template_values[arg_name] = arg_schema["default"]
            else:
                # Generate appropriate placeholder based on type
                arg_type = arg_schema.get("type", "string")
                description = arg_schema.get("description", f"Value for {arg_name}")

                if arg_type == "string":
                    # Create a descriptive placeholder
                    template_values[arg_name] = f"<Enter {description.lower()}>"
                elif arg_type == "boolean":
                    template_values[arg_name] = False
                elif arg_type in ["integer", "number"]:
                    template_values[arg_name] = 0
                elif arg_type == "array":
                    template_values[arg_name] = []
                elif arg_type == "object":
                    template_values[arg_name] = {}
                else:
                    # Default to descriptive string placeholder
                    template_values[arg_name] = f"<Enter {description.lower()}>"

        return template_values

    def action_reset_defaults(self):
        """Reset default values to create template JSON from prompt's arguments schema"""
        self.ensure_one()

        if not self.prompt_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Prompt Template',
                    'message': 'Please select a prompt template first.',
                    'type': 'warning',
                }
            }

        try:
            # Get the prompt arguments schema
            args_schema = json.loads(self.prompt_id.arguments_json or "{}")

            if not args_schema:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'No Arguments Schema',
                        'message': 'The selected prompt template has no arguments schema defined.',
                        'type': 'info',
                    }
                }

            # Generate template JSON from schema
            template_values = self._generate_template_json_from_schema(args_schema)

            # Update default_values field with pretty-formatted JSON
            self.default_values = json.dumps(template_values, indent=2)

            # Count how many were defaults vs placeholders
            defaults_count = sum(1 for arg_schema in args_schema.values() if "default" in arg_schema)
            placeholders_count = len(template_values) - defaults_count

            message_parts = []
            if defaults_count > 0:
                message_parts.append(f"{defaults_count} default values")
            if placeholders_count > 0:
                message_parts.append(f"{placeholders_count} placeholder values")

            message = f"Template JSON created with {' and '.join(message_parts)}."

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Template JSON Generated',
                    'message': message,
                    'type': 'success',
                    'next': {
                        'type': 'ir.actions.client',
                        'tag': 'reload',
                    }
                }
            }

        except json.JSONDecodeError:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': 'Invalid JSON in prompt arguments schema.',
                    'type': 'danger',
                }
            }
        except Exception as e:
            _logger.error("Error resetting defaults for assistant %s: %s", self.name, str(e))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': f'Error generating template JSON: {str(e)}',
                    'type': 'danger',
                }
            }

    def get_evaluated_default_values(self, context):
        """
        Evaluate default values using the provided context.
        This is used by llm.thread to get assistant's default values with thread context.

        Args:
            context (dict): Context for template rendering

        Returns:
            dict: Evaluated default values
        """
        self.ensure_one()

        # Parse the default values JSON
        try:
            default_values = json.loads(self.default_values or "{}")
        except json.JSONDecodeError:
            _logger.warning("Invalid JSON in default_values for assistant %s", self.name)
            return {}

        if not default_values:
            return {}

        # If we don't have dynamic defaults, return as-is
        if not self.has_dynamic_defaults:
            return default_values

        # Render each default value as a template
        evaluated_values = {}
        for key, value in default_values.items():
            if isinstance(value, str) and "{{" in value and "}}" in value:
                try:
                    evaluated_values[key] = render_template(template=value, context=context)
                except Exception as e:
                    _logger.warning("Error evaluating default value '%s' for assistant %s: %s", key, self.name, str(e))
                    evaluated_values[key] = value  # Keep original on error
            else:
                evaluated_values[key] = value

        return evaluated_values

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to ensure default_values is valid JSON"""
        for vals in vals_list:
            if "default_values" in vals and vals["default_values"]:
                try:
                    json.loads(vals["default_values"])
                except json.JSONDecodeError:
                    vals["default_values"] = "{}"
        return super().create(vals_list)

    @api.onchange("prompt_id")
    def _onchange_prompt_id(self):
        """Update default_values when prompt_id changes to create template JSON

        ONLY triggers when prompt_id actually changes, not on every field change.
        """
        # Only proceed if we have a prompt_id and this is actually a change in prompt_id
        if not self.prompt_id:
            return

        # Check if this is a new record or if prompt_id actually changed
        if self._origin.prompt_id == self.prompt_id:
            # No change in prompt_id, don't regenerate defaults
            return

        # Get the prompt arguments schema
        try:
            args_schema = json.loads(self.prompt_id.arguments_json or "{}")

            # If there are arguments defined, generate template JSON
            if args_schema:
                template_values = self._generate_template_json_from_schema(args_schema)
                self.default_values = json.dumps(template_values, indent=2)
            else:
                # No arguments schema, keep empty JSON
                self.default_values = "{}"

        except json.JSONDecodeError:
            # Invalid JSON in arguments_json, keep empty
            self.default_values = "{}"

    def _get_json_fields(self):
        """Return fields that should be serialized as JSON in the API"""
        return ["default_values"]

    @api.model
    def get_assistant_by_id(self, assistant_id):
        """Get an assistant record by its ID

        Args:
            assistant_id (int): ID of the assistant

        Returns:
            tuple: (assistant, error_response)
                  If successful, error_response will be None
                  If error, assistant will be None
        """
        if not assistant_id:
            return None, None

        assistant = self.browse(int(assistant_id))
        if not assistant.exists():
            return None, {"success": False, "error": "Assistant not found"}
        return assistant, None

    def get_assistant_values(self, thread, include_prompt=True):
        """Get thread-specific evaluated default values for this assistant

        Args:
            thread (llm.thread): Thread record
            include_prompt (bool): Whether to include prompt data

        Returns:
            dict: Result with evaluated default values and prompt data
        """
        self.ensure_one()

        # Get thread context and use it to evaluate default values
        thread_context = thread.get_context() if hasattr(thread, 'get_context') else {}
        evaluated_values = self.get_evaluated_default_values(thread_context)

        result = {
            "success": True,
            "thread_id": thread.id,
            "assistant_id": self.id,
            "default_values": self.default_values,
            "evaluated_default_values": json.dumps(evaluated_values, indent=2) if evaluated_values else "{}",
        }

        # Get the prompt details if requested
        if include_prompt and self.prompt_id:
            prompt = self.prompt_id
            result["prompt"] = {
                "id": prompt.id,
                "name": prompt.name,
                "input_schema_json": prompt.input_schema_json,
            }

        return result

    def _get_allowed_assistants_for_user(self, user=None):
        """Get assistants that the current user can access"""
        if not user:
            user = self.env.user

        # Admin can access all assistants
        if user.has_group("base.group_system"):
            return self.search([])

        # Assistants allowed for user's groups
        if user.groups_id:
            domain = [
                "|",
                ("is_public", "=", True),
                ("allowed_group_ids", "in", user.groups_id.ids),
            ]
        else:
            # If user has no groups, only public assistants
            domain = [("is_public", "=", True)]

        return self.search(domain)
