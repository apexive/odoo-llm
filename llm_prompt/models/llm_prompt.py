import json
import logging
import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

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

    # Templates
    template_ids = fields.One2many(
        "llm.prompt.template",
        "prompt_id",
        string="Templates",
        help="Sequence of templates in a multi-step prompt",
    )
    template_count = fields.Integer(
        compute="_compute_template_count",
        string="Template Count",
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

    # Example invocation
    example_args = fields.Text(
        string="Example Arguments",
        help="Example arguments in JSON format to test this prompt",
        default="""{}""",
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

    @api.depends("template_ids")
    def _compute_template_count(self):
        for prompt in self:
            prompt.template_count = len(prompt.template_ids)

    @api.depends("arguments_json")
    def _compute_argument_count(self):
        for prompt in self:
            try:
                arguments = json.loads(prompt.arguments_json or "{}")
                prompt.argument_count = len(arguments)
            except json.JSONDecodeError:
                prompt.argument_count = 0

    @api.depends("arguments_json", "template_ids.content")
    def _compute_argument_validation(self):
        for prompt in self:
            # Get defined arguments
            try:
                arguments = json.loads(prompt.arguments_json or "{}")
                defined_args = set(arguments.keys())
            except json.JSONDecodeError:
                defined_args = set()

            # Extract used arguments from templates
            used_args = set()

            # Check templates
            for template in prompt.template_ids:
                if template.content:
                    template_args = self._extract_arguments_from_template(
                        template.content
                    )
                    used_args.update(template_args)

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

    @api.constrains("example_args")
    def _validate_example_args_syntax(self):
        """Validate that the example args JSON is syntactically valid"""
        for prompt in self:
            if not prompt.example_args:
                continue

            try:
                json.loads(prompt.example_args)
            except json.JSONDecodeError as e:
                raise ValidationError(
                    _("Invalid JSON in example arguments: %s") % str(e)
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
        arguments = self._fill_default_values(arguments)

        # Validate arguments against schema
        self._validate_arguments(arguments)

        messages = []

        # Add template messages
        for template in self.template_ids.sorted(key=lambda t: t.sequence):
            template_message = template.get_template_message(arguments)
            if template_message:
                messages.append(template_message)

        # Update usage statistics
        self.usage_count += 1
        self.last_used = fields.Datetime.now()

        return messages

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
            # If schema is invalid, skip validation
            return

        # Check for required arguments
        for arg_name, arg_schema in schema.items():
            if arg_schema.get("required", False) and arg_name not in arguments:
                raise ValidationError(_("Missing required argument: %s") % arg_name)

        # Handle special types like context and resource
        for arg_name, value in arguments.items():
            if arg_name in schema:
                arg_type = schema[arg_name].get("type")

                # Handle context type (automatically filled from Odoo context)
                if arg_type == "context" and not value:
                    # This would be filled in runtime
                    pass

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
        pattern = r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}"
        matches = re.findall(pattern, template_content)

        return set(matches)

    def auto_detect_arguments(self):
        """
        Auto-detect arguments from templates and add them to schema

        Returns:
            bool: True if successful
        """
        self.ensure_one()

        # Get existing arguments
        try:
            arguments = json.loads(self.arguments_json or "{}")
        except json.JSONDecodeError:
            arguments = {}

        # Extract used arguments from templates
        used_args = set()

        # Check templates
        for template in self.template_ids:
            if template.content:
                template_args = self._extract_arguments_from_template(template.content)
                used_args.update(template_args)

        # Add any missing arguments to schema
        updated = False
        for arg_name in used_args:
            if arg_name not in arguments:
                arguments[arg_name] = {
                    "type": "string",
                    "description": f"Auto-detected argument: {arg_name}",
                    "required": False,
                }
                updated = True

        if updated:
            self.arguments_json = json.dumps(arguments, indent=2)

        return True

    def action_test_prompt(self):
        """
        Test the prompt with example arguments

        Returns:
            dict: Action to show test result
        """
        self.ensure_one()

        try:
            example_args = json.loads(self.example_args or "{}")
        except json.JSONDecodeError as e:
            raise ValidationError(_("Invalid example arguments JSON")) from e

        messages = self.get_messages(example_args)

        # Create a wizard to show the result
        wizard = self.env["llm.prompt.test"].create(
            {
                "prompt_id": self.id,
                "messages": json.dumps(messages, indent=2),
            }
        )

        return {
            "name": _("Prompt Test Result"),
            "type": "ir.actions.act_window",
            "res_model": "llm.prompt.test",
            "view_mode": "form",
            "res_id": wizard.id,
            "target": "new",
        }

    def get_formatted_system_prompt(self, default_values=None):
        """Generate a formatted system prompt based on the prompt template"""
        self.ensure_one()

        try:
            # Get the argument values from default_values
            arg_values = json.loads(default_values or "{}")

            # Get messages from the prompt template
            messages = self.get_messages(arg_values)

            # Find the system message
            system_message = next(
                (msg for msg in messages if msg.get("role") == "system"), None
            )
            if system_message and "content" in system_message:
                if (
                    isinstance(system_message["content"], dict)
                    and "text" in system_message["content"]
                ):
                    return system_message["content"]["text"]
                elif isinstance(system_message["content"], str):
                    return system_message["content"]

            # If no system message found, return the first message content
            if messages and "content" in messages[0]:
                if (
                    isinstance(messages[0]["content"], dict)
                    and "text" in messages[0]["content"]
                ):
                    return messages[0]["content"]["text"]
                elif isinstance(messages[0]["content"], str):
                    return messages[0]["content"]

        except Exception as e:
            _logger.error("Error generating system prompt from template: %s", str(e))
            return _("Error generating system prompt preview: %s") % str(e)

    @api.depends("template_ids", "arguments_json")
    def _compute_input_schema_json(self):
        """
        Compute a proper JSON schema for input fields based on the first template and arguments_json.
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
