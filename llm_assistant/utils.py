import logging

from jinja2 import Environment, Undefined

from odoo import _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


def render_template(template=None, context=None):
    """
    Replace argument placeholders in content with their values using Jinja2.

    Args:
        context (dict): Dictionary of argument values

    Returns:
        str: Content with placeholders replaced by values
        :param context:
        :param template:
    """
    # Make a copy of context to avoid modifying the original
    context_copy = dict(context)

    # Process boolean values for JSON compatibility
    processed_args = {}
    for arg_name, arg_value in context_copy.items():
        if isinstance(arg_value, bool):
            # Convert Python True/False to JSON true/false
            processed_args[arg_name] = "true" if arg_value else "false"
        else:
            processed_args[arg_name] = arg_value

    # Create Jinja2 environment
    env = Environment(
        variable_start_string="{{",
        variable_end_string="}}",
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=Undefined,  # Handle missing variables gracefully
    )

    # Create and render the template
    try:
        template = env.from_string(template)
        return template.render(**processed_args)
    except Exception as e:
        raise ValidationError(
            _(
                "Could not process the prompt template. Check that all placeholder "
                "variables ({{variable}}) are correctly named and the template syntax is valid.\n\n"
                "Details: %s"
            )
            % str(e)
        ) from e
