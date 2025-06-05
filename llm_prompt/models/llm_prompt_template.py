import json
import logging

from jinja2 import Environment, Undefined

from odoo import _, api, fields, models
from odoo.tools import safe_eval

_logger = logging.getLogger(__name__)


class LLMPromptTemplate(models.Model):
    _name = "llm.prompt.template"
    _description = "LLM Prompt Template"
    _order = "sequence, id"

    sequence = fields.Integer(
        string="Sequence",
        default=10,
        help="Order in which templates are processed",
    )
    prompt_id = fields.Many2one(
        "llm.prompt",
        string="Prompt",
        required=True,
        ondelete="cascade",
    )

    # Template role
    role = fields.Selection(
        [
            ("user", "User"),
            ("assistant", "Assistant"),
            ("system", "System"),
        ],
        string="Role",
        default="user",
        required=True,
        help="Role of this template in the conversation",
    )

    # Content
    content = fields.Text(
        string="Content",
        required=True,
        help="Content of this template with placeholders for arguments (use {{argument_name}})",
    )

    # Conditional execution
    condition = fields.Char(
        string="Execution Condition",
        help="Python expression determining whether to include this template (e.g., 'debug' in arguments)",
    )

    # Computed field to show used arguments
    used_arguments = fields.Char(
        string="Used Arguments",
        compute="_compute_used_arguments",
        help="Arguments used in this template",
    )

    @api.depends("content")
    def _compute_used_arguments(self):
        """Compute arguments used in this template"""
        for template in self:
            if not template.content:
                template.used_arguments = ""
                continue

            args = template.prompt_id._extract_arguments_from_template(template.content)
            template.used_arguments = ", ".join(sorted(args)) if args else ""

    def _substitute_placeholders(self, content, arguments):
        """
        Replace argument placeholders in content with their values using Jinja2.
        Extends the base implementation to handle special cases:
        1. When arg_name is 'related_record', fetch from llm.thread.get_related_record()
        2. When placeholder is like {{get_related_record('field_name')}}, get the field value from the record

        Args:
            content (str): Content with placeholders
            arguments (dict): Dictionary of argument values

        Returns:
            str: Content with placeholders replaced by values
        """
        # Process boolean values for JSON compatibility
        processed_args = dict(arguments)
        for arg_name, arg_value in arguments.items():
            if isinstance(arg_value, bool):
                # Convert Python True/False to JSON true/false
                processed_args[arg_name] = "true" if arg_value else "false"
            else:
                processed_args[arg_name] = arg_value

        # Create Jinja2 environment with custom functions
        env = Environment(
            variable_start_string="{{",
            variable_end_string="}}",
            trim_blocks=True,
            lstrip_blocks=True,
            undefined=Undefined,  # Handle missing variables gracefully
        )

        # Get related record if available
        related_record = None
        thread = self.env["llm.thread"].get_thread_from_context()
        if thread:
            related_record = thread.get_related_record()
            if related_record:
                # Add related_record to the context
                processed_args["related_record"] = json.dumps(
                    {
                        "model": related_record._name,
                        "id": related_record.id,
                        "display_name": related_record.display_name,
                    }
                )

        # Create a wrapper function that automatically includes the related_record
        def get_related_record_wrapper(field_name, key_name=None):
            return self.get_related_record(field_name, key_name, related_record)

        # Always register the function, even if related_record is None
        env.globals["get_related_record"] = get_related_record_wrapper

        # Create and render the template
        template = env.from_string(content)
        return template.render(**processed_args)

    def get_related_record(self, field_name, key_name=None, related_record=None):
        """
        Access fields or dictionary keys from a related record.

        Args:
            field_name (str): The field name to access
            key_name (str, optional): If the field is a dictionary, the key to access
            related_record (Model, optional): The record to access.

        Returns:
            str: The value of the field/key or an empty string if not available
        """
        # If we still don't have a related record, return empty string
        if not related_record:
            _logger.info(
                "No related record available, returning empty value for %s", field_name
            )
            return ""

        # Access the field
        if hasattr(related_record, field_name):
            try:
                attr_value = getattr(related_record, field_name)

                if (
                    key_name is not None
                ):  # We want to access an item from this attribute
                    if isinstance(attr_value, dict):
                        if key_name in attr_value:
                            final_value = attr_value[key_name]
                        else:
                            _logger.warning(
                                "Key '%s' not found in dictionary field '%s'",
                                key_name,
                                field_name,
                            )
                            result = ""  # Return empty string instead of error message
                    else:
                        _logger.warning(
                            "Field '%s' is not a dictionary, cannot access key '%s'",
                            field_name,
                            key_name,
                        )
                        result = ""  # Return empty string instead of error message
                else:  # No key, just return the attribute value
                    result = attr_value

                # Convert to string with proper JSON handling for booleans
                if isinstance(result, bool):
                    return "true" if final_value else "false"
                return result

            except Exception as e:
                _logger.error(
                    "Error getting field %s (key: %s) from record: %s",
                    field_name,
                    key_name,
                    str(e),
                )
                return ""  # Return empty string instead of error message
        else:
            _logger.warning("Record doesn't have field: %s", field_name)
            return ""  # Return empty string instead of error message

    def get_template_message(self, arguments=None):
        """
        Generate a message for this template with the given arguments

        Args:
            arguments (dict): Dictionary of argument values

        Returns:
            dict: Message dictionary for this template
        """
        self.ensure_one()
        arguments = arguments or {}

        # Check if condition is satisfied
        if self.condition:
            try:
                if not self._evaluate_condition(self.condition, arguments):
                    return None
            except Exception as e:
                # Log but don't fail if condition evaluation fails
                self.prompt_id.message_post(
                    body=_("Error evaluating condition for template %s: %s")
                    % (self.id, str(e))
                )
                return None

        # Replace argument placeholders in content
        content = self._substitute_placeholders(self.content, arguments)

        # Create the message
        return {
            "role": self.role,
            "content": [
                {
                    "type": "text",
                    "text": content,
                }
            ],
        }

    def _evaluate_condition(self, condition, arguments):
        """Evaluate the execution condition"""
        # Create a safe evaluation context with just the arguments
        eval_context = {"arguments": arguments}
        # Add common operators
        for k in arguments:
            eval_context[k] = arguments[k]

        # Evaluate the condition expression
        return safe_eval(condition, {"__builtins__": {}}, eval_context)
