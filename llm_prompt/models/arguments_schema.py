import json

import jsonschema

from odoo import _

# Schema for individual argument objects
ARGUMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": [
                "string",
                "number",
                "integer",
                "boolean",
                "array",
                "object",
                "resource",
                "context",
            ],
        },
        "description": {"type": "string"},
        "required": {"type": "boolean"},
        "default": {},  # Any type allowed
        "examples": {"type": "array"},
    },
    "additionalProperties": True,  # Allow any other properties for flexibility
}

# Schema for the complete arguments_json field
ARGUMENTS_JSON_SCHEMA = {
    "type": "object",
    "patternProperties": {"^[a-zA-Z0-9_]+$": ARGUMENT_SCHEMA},
    "additionalProperties": False,
}


def validate_arguments_schema(schema_text):
    """
    Validate an arguments schema against the ARGUMENTS_JSON_SCHEMA.

    Args:
        schema_text (str): JSON string to validate

    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        schema = json.loads(schema_text)
        jsonschema.validate(instance=schema, schema=ARGUMENTS_JSON_SCHEMA)
        return True, ""
    except json.JSONDecodeError as e:
        return False, _("Invalid JSON: %s") % str(e)
    except jsonschema.exceptions.ValidationError as e:
        path = ".".join(str(p) for p in e.path) if e.path else ""
        message = f"{path}: {e.message}" if path else e.message
        return False, _("Schema validation error: %s") % message
    except Exception as e:
        return False, _("Validation error: %s") % str(e)
