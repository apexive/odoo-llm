import json
import logging
import re
from collections.abc import Iterable

import yaml

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from ..utils import render_template
from .arguments_schema import validate_arguments_schema

_logger = logging.getLogger(__name__)


class LLMPrompt(models.Model):
    _name = "llm.prompt"
    _description = "LLM Prompt Template"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char(
        string="Prompt Name",
        required=True,
        tracking=True,
        help="Unique identifier for the prompt template",
    )
    description = fields.Text(
        string="Description",
        tracking=True,
        help="Human-readable description of the prompt",
    )
    active = fields.Boolean(default=True)

    # Categorization
    category_id = fields.Many2one(
        "llm.prompt.category",
        string="Category",
        tracking=True,
        index=True,
        help="Category for organizing prompts",
    )

    # Tags
    tag_ids = fields.Many2many(
        "llm.prompt.tag",
        "llm_prompt_tag_rel",
        "prompt_id",
        "tag_id",
        string="Tags",
        help="Classify and analyze your prompts",
    )

    # Provider and Publisher relations
    provider_ids = fields.Many2many(
        "llm.provider",
        "llm_prompt_provider_rel",
        "prompt_id",
        "provider_id",
        string="Compatible Providers",
        help="LLM providers that can use this prompt",
    )

    publisher_ids = fields.Many2many(
        "llm.publisher",
        "llm_prompt_publisher_rel",
        "prompt_id",
        "publisher_id",
        string="Compatible Publishers",
        help="LLM publishers whose models work well with this prompt",
    )

    # Template field
    template = fields.Text(
        string="Template",
        required=True,
        help="Prompt template content in the selected format",
        tracking=True,
    )

    # Format selection
    format = fields.Selection(
        [
            ("text", "Text"),
            ("yaml", "YAML"),
            ("json", "JSON"),
        ],
        string="Format",
        default="text",
        required=True,
        tracking=True,
        help="Format of the template content after rendering",
    )

    # Arguments JSON field
    arguments_json = fields.Text(
        string="Arguments Schema",
        help="JSON object defining all arguments used in this prompt",
        default="""{}""",
        tracking=True,
    )

    # Computed fields for argument info
    argument_count = fields.Integer(
        compute="_compute_argument_count",
        string="Argument Count",
    )

    undefined_arguments = fields.Char(
        compute="_compute_argument_validation",
        string="Undefined Arguments",
        help="Arguments used in templates but not defined in schema",
    )

    # Usage tracking
    usage_count = fields.Integer(
        string="Usage Count",
        default=0,
        readonly=True,
        help="Number of times this prompt has been used",
    )
    last_used = fields.Datetime(
        string="Last Used",
        readonly=True,
        help="When this prompt was last used",
    )

    input_schema_json = fields.Json(
        string="Input Schema JSON",
        compute="_compute_input_schema_json",
        help="JSON schema for input fields",
        store=True,
    )

    _sql_constraints = [
        ("name_unique", "UNIQUE(name)", "The prompt name must be unique."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        prompts = super().create(vals_list)
        return prompts

    def write(self, vals):
        result = super().write(vals)
        return result

    def copy(self, default=None):
        """Override copy to generate unique name with auto-increment pattern"""
        self.ensure_one()

        if default is None:
            default = {}

        if "name" not in default:
            # Generate unique name with (Copy N) pattern
            base_name = self.name
            copy_name = self._generate_unique_copy_name(base_name)
            default["name"] = copy_name

        return super().copy(default=default)

    def _generate_unique_copy_name(self, base_name):
        """Generate unique name with (Copy N) pattern"""
        # Check if base_name already has (Copy N) pattern
        import re

        copy_pattern = r"^(.+) \(Copy (\d+)\)$"
        match = re.match(copy_pattern, base_name)

        if match:
            # Extract original name without (Copy N)
            original_name = match.group(1)
        else:
            # Use the full name as original
            original_name = base_name

        # Find existing copies with this base name
        like_pattern = f"{original_name}%"
        existing_records = self.search([("name", "=like", like_pattern)])

        # Extract all copy numbers
        copy_numbers = []
        for record in existing_records:
            if record.name == original_name:
                # Original name exists, so we need Copy 1, 2, etc.
                copy_numbers.append(0)
            else:
                match = re.match(
                    rf"^{re.escape(original_name)} \(Copy (\d+)\)$", record.name
                )
                if match:
                    copy_numbers.append(int(match.group(1)))

        # Find next available number
        if not copy_numbers:
            # No existing copies, start with Copy 1
            next_number = 1
        else:
            # Find the next available number
            next_number = max(copy_numbers) + 1

        return f"{original_name} (Copy {next_number})"

    @api.depends("arguments_json")
    def _compute_argument_count(self):
        for prompt in self:
            try:
                arguments = json.loads(prompt.arguments_json or "{}")
                prompt.argument_count = len(arguments)
            except json.JSONDecodeError:
                prompt.argument_count = 0

    @api.depends("arguments_json", "template")
    def _compute_argument_validation(self):
        for prompt in self:
            # Get defined arguments
            try:
                arguments = json.loads(prompt.arguments_json or "{}")
                defined_args = set(arguments.keys())
            except json.JSONDecodeError:
                defined_args = set()

            # Extract used arguments from template
            used_args = self._extract_arguments_from_template(prompt.template or "")

            # Find undefined arguments
            undefined_args = [name for name in used_args if name not in defined_args]

            if undefined_args:
                prompt.undefined_arguments = ", ".join(undefined_args)
            else:
                prompt.undefined_arguments = False

    @api.constrains("arguments_json")
    def _validate_arguments_schema(self):
        """Validate arguments JSON against schema"""
        for prompt in self:
            if not prompt.arguments_json:
                continue

            is_valid, error = validate_arguments_schema(prompt.arguments_json)
            if not is_valid:
                raise ValidationError(error)

    def _validate_rendered_format(self, rendered_content):
        """
        Validate rendered content matches the selected format

        Args:
            rendered_content (str): The rendered template content

        Raises:
            ValidationError: If rendered content doesn't match format
        """
        if not rendered_content:
            return

        try:
            if self.format == "json":
                json.loads(rendered_content)
            elif self.format == "yaml":
                # For YAML, we need to handle multiple documents
                list(yaml.safe_load_all(rendered_content))
            # Text format doesn't need validation
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise ValidationError(
                _(
                    "The rendered template is not valid %s.\n\n"
                    "Please check your template syntax and ensure it produces valid %s "
                    "output after variable substitution.\n\n"
                    "Error: %s"
                )
                % (self.format.upper(), self.format.upper(), str(e))
            ) from e

    def get_prompt_data(self):
        """Returns the prompt data in the MCP format"""
        self.ensure_one()

        # Parse arguments
        try:
            arguments = json.loads(self.arguments_json or "{}")
        except json.JSONDecodeError:
            arguments = {}

        # Format arguments for MCP
        formatted_args = []
        for name, schema in arguments.items():
            arg_data = {
                "name": name,
                "description": schema.get("description", ""),
                "required": schema.get("required", False),
            }
            formatted_args.append(arg_data)

        return {
            "name": self.name,
            "description": self.description or "",
            "category": self.category_id.name if self.category_id else "",
            "arguments": formatted_args,
        }

    def get_default_test_context(self):
        """
        Get default test context based on prompt's arguments schema.

        Returns:
            dict: Default context for testing
        """
        try:
            schema = json.loads(self.arguments_json or "{}")
            defaults = {}
            for arg_name, arg_schema in schema.items():
                if "default" in arg_schema:
                    defaults[arg_name] = arg_schema["default"]
                elif arg_schema.get("type") == "string":
                    defaults[arg_name] = f"sample_{arg_name}"
                elif arg_schema.get("type") == "number":
                    defaults[arg_name] = 42
                elif arg_schema.get("type") == "boolean":
                    defaults[arg_name] = True
                elif arg_schema.get("type") == "array":
                    defaults[arg_name] = ["item1", "item2"]
                else:
                    defaults[arg_name] = f"sample_{arg_name}"

            return defaults
        except (json.JSONDecodeError, Exception):
            return {}

    def get_messages(self, arguments=None):
        """
        Generate messages for this prompt with the given arguments

        Args:
            arguments (dict): Dictionary of argument values

        Returns:
            list: List of messages for this prompt
        """
        self.ensure_one()
        arguments = arguments or {}

        # Fill default values for missing arguments
        arguments = self.sudo()._fill_default_values(arguments)

        # Validate arguments against schema
        self._validate_arguments(arguments)

        # Render the template with arguments
        rendered_content = render_template(template=self.template, context=arguments)

        # Validate the rendered content matches the expected format
        self._validate_rendered_format(rendered_content)

        # Parse template based on format
        try:
            if self.format == "text":
                messages = self._parse_text_messages(rendered_content)
            elif self.format == "yaml":
                messages = list(
                    self._parse_dict_messages(yaml.safe_load_all(rendered_content))
                )
            elif self.format == "json":
                messages = list(self._parse_dict_messages(json.loads(rendered_content)))
            else:
                raise ValidationError(
                    _(
                        "The template format '%s' is not supported. "
                        "Please use Text, YAML, or JSON format."
                    )
                    % self.format
                )
        except ValidationError:
            raise
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            _logger.error(
                "Error parsing %s rendered content for prompt %s: %s",
                self.format,
                self.name,
                str(e),
            )
            raise ValidationError(
                _(
                    "Could not parse the rendered %s content. The template may have "
                    "syntax errors or produce invalid output.\n\n"
                    "Tips:\n"
                    "• For YAML: Check indentation and special characters\n"
                    "• For JSON: Ensure quotes and brackets are balanced\n\n"
                    "Details: %s"
                )
                % (self.format.upper(), str(e))
            ) from e

        return messages

    def _parse_text_messages(self, content):
        """Parse a simple text template"""
        return [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": content,
                    }
                ],
            }
        ]

    def _parse_dict_messages(self, data):
        """Parse messages from dict, list, or iterator of dicts recursively"""

        # Handle single dict or iterable of items
        items = (
            data
            if isinstance(data, Iterable) and not isinstance(data, (str, dict))
            else [data]
        )

        for item in items:
            if isinstance(item, dict):
                # Check if this dict has a 'content' key - if so, it's a message
                if "content" in item:
                    msg_type = item.get("type", "user")
                    content = item["content"]

                    # Handle multi-line content
                    if isinstance(content, list):
                        content = "\n".join(str(line) for line in content)

                    yield {
                        "role": msg_type,
                        "content": [
                            {
                                "type": "text",
                                "text": str(content),
                            }
                        ],
                    }
                else:
                    # If no 'content' key, recursively check all values in the dict
                    for value in item.values():
                        if isinstance(value, (dict, list)) or (
                            isinstance(value, Iterable) and not isinstance(value, str)
                        ):
                            yield from self._parse_dict_messages(value)

            elif isinstance(item, (list, tuple)) or (
                isinstance(item, Iterable) and not isinstance(item, str)
            ):
                # If item is iterable (but not string), recurse into it
                yield from self._parse_dict_messages(item)

    def _fill_default_values(self, arguments):
        """
        Fill in default values for missing arguments

        Args:
            arguments (dict): Provided argument values

        Returns:
            dict: Arguments with defaults filled in
        """
        result = arguments.copy()

        try:
            schema = json.loads(self.arguments_json or "{}")
        except json.JSONDecodeError:
            return result

        # Add default values for missing arguments
        for arg_name, arg_schema in schema.items():
            if arg_name not in result and "default" in arg_schema:
                result[arg_name] = arg_schema["default"]

        return result

    def _validate_arguments(self, arguments):
        """
        Validate provided arguments against the schema

        Args:
            arguments (dict): Dictionary of argument values

        Raises:
            ValidationError: If arguments are invalid
        """
        self.ensure_one()

        try:
            schema = json.loads(self.arguments_json or "{}")
        except json.JSONDecodeError:
            _logger.warning(
                "Skipping: Invalid JSON in arguments schema: %s", self.arguments_json
            )
            return

        # Check for required arguments
        for arg_name, arg_schema in schema.items():
            if arg_schema.get("required", False) and arg_name not in arguments:
                raise ValidationError(
                    _(
                        "The required argument '%s' is missing. "
                        "Please provide a value for this argument before running the prompt."
                    )
                    % arg_name
                )

    @api.model
    def _extract_arguments_from_template(self, template_content):
        """
        Extract argument names from a template string.

        Args:
            template_content (str): The template content to search

        Returns:
            set: Set of argument names found in the template
        """
        if not template_content:
            return set()

        # Find all {{argument}} placeholders
        # Match simple variables: {{variable_name}}
        simple_pattern = r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}"
        simple_matches = re.findall(simple_pattern, template_content)

        return set(simple_matches)

    def auto_detect_arguments(self):
        """
        Auto-detect arguments from template and add them to schema

        Returns:
            bool: True if successful
        """
        self.ensure_one()

        # Get existing arguments
        try:
            arguments = json.loads(self.arguments_json or "{}")
        except json.JSONDecodeError:
            arguments = {}

        # Extract used arguments from template
        used_args = self._extract_arguments_from_template(self.template or "")

        # Add any missing arguments to schema
        updated = False
        for arg_name in used_args:
            if arg_name not in arguments:
                arguments[arg_name] = {
                    "type": "string",
                    "description": f"Auto-detected argument: {arg_name}",
                    "required": True,  # Default new arguments as required
                }
                updated = True

        if updated:
            self.arguments_json = json.dumps(arguments, indent=2)

        return True

    def _ensure_arguments_sync(self):
        """Ensure arguments schema matches template usage"""
        used_args = self._extract_arguments_from_template(self.template or "")
        try:
            defined_args = json.loads(self.arguments_json or "{}")
        except json.JSONDecodeError:
            defined_args = {}

        # Auto-add missing arguments
        updated = False
        for arg_name in used_args:
            if arg_name not in defined_args:
                defined_args[arg_name] = {
                    "type": "string",
                    "description": f"Auto-detected argument: {arg_name}",
                    "required": True,  # Default new arguments as required
                }
                updated = True

        if updated:
            self.arguments_json = json.dumps(defined_args, indent=2)

    def action_test_prompt(self):
        """
        Test the prompt with the enhanced evaluation wizard

        Returns:
            dict: Action to show enhanced test wizard
        """
        self.ensure_one()

        # Create a wizard record with the prompt pre-filled
        wizard = self.env["llm.prompt.test"].create(
            {
                "prompt_id": self.id,
            }
        )

        return {
            "name": _("Test Prompt: %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "llm.prompt.test",
            "view_mode": "form",
            "res_id": wizard.id,
            "target": "new",
            "view_id": self.env.ref("llm_assistant.llm_prompt_test_view_form").id,
            "context": {
                "default_prompt_id": self.id,
            },
        }

    @api.depends("template", "arguments_json")
    def _compute_input_schema_json(self):
        """
        Compute a proper JSON schema for input fields based on the template and arguments_json.
        This is used for media generation models to provide a customized input form.
        """
        for prompt in self:
            try:
                # Get arguments from arguments_json
                arguments = json.loads(prompt.arguments_json or "{}")

                prompt.input_schema_json = self._generate_json_schema(arguments)
            except Exception as e:
                _logger.error("Error computing input schema JSON: %s", str(e))
                prompt.input_schema_json = {}

    def _generate_json_schema(self, input_json):
        # Initialize dictionaries and lists for schema components
        properties = {}
        required = []

        # Process each property from the input dictionary
        for prop_name, prop_details in input_json.items():
            # Create a copy of prop_details to avoid modifying the original
            prop_schema = dict(prop_details)

            # Check if the property is required and add to the required list if true
            if prop_schema.get("required", False):
                required.append(prop_name)
                # Remove the required key from the property schema
                prop_schema.pop("required", None)

            # Add the property schema to the properties dictionary
            properties[prop_name] = prop_schema

        # Construct the full JSON schema
        schema = {
            "type": "object",
            "properties": properties,
        }

        # Only add required array if there are required fields
        if required:
            schema["required"] = required

        # Return the schema as a Python dictionary
        return schema
