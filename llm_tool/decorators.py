"""LLM Tool Decorators for easy tool creation"""

import inspect
import logging
from functools import wraps

_logger = logging.getLogger(__name__)


def llm_tool(
    func=None,
    *,
    name=None,
    description=None,
    xml_managed=False,
    schema=None,
    **metadata,
):
    """
    Decorator to mark a method as an LLM tool.

    Automatically extracts:
    - name: from function name (or override with name parameter)
    - description: from docstring (or override with description parameter)
    - schema: from type hints (or accepts manual schema)

    This decorator:
    1. Validates that the method has proper type hints OR accepts manual schema
    2. Marks the method so it can be linked to llm.tool records
    3. Stores metadata on the function for later retrieval

    Tool Registration Modes:
    - xml_managed=False (default): Tool is auto-created by _register_hook()
    - xml_managed=True: Tool must be defined in XML data file (Odoo standard pattern)
                        _register_hook() completely skips this tool

    Usage (simple - auto-registers, no external ID):
        class SaleOrder(models.Model):
            _inherit = 'sale.order'

            @llm_tool
            def create_sales_quote(
                self,
                customer_name: str,
                products: list[str]
            ) -> dict:
                \"\"\"Create a sales quotation for a customer with specified products\"\"\"
                # Implementation
                return {"quote_id": 123}

    Usage (XML-managed - full control via XML data file):
        # In Python:
        @llm_tool(
            name="my_tool",
            xml_managed=True,  # Tool defined in XML, skip auto-registration
            read_only_hint=True,
        )
        def my_tool_method(self, param: str) -> dict:
            \"\"\"Tool implementation\"\"\"
            return {"result": param}

        # In XML (data/llm_tool_data.xml):
        <record id="my_tool" model="llm.tool">
            <field name="name">my_tool</field>
            <field name="implementation">function</field>
            <field name="decorator_model">my.model</field>
            <field name="decorator_method">my_tool_method</field>
            <field name="description">My tool description</field>
        </record>

    Usage (with manual schema for legacy methods):
        @llm_tool(schema={
            "type": "object",
            "properties": {
                "partner_id": {"type": "integer"},
                "amount": {"type": "number"}
            },
            "required": ["partner_id", "amount"]
        })
        def create_invoice(self, partner_id, amount):
            \"\"\"Create an invoice for a partner\"\"\"
            # Existing Odoo method without type hints
            return {"invoice_id": 456}

    Args:
        func: The function to decorate (when using @llm_tool without parentheses)
        name: Optional tool name (defaults to function name)
        description: Optional description (defaults to docstring)
        xml_managed: If True, tool is defined in XML data file. _register_hook()
                     will completely skip this tool (no insert, update, or deactivate).
                     XML has full control. Default: False (auto-register)
        schema: Optional manual JSON schema (for methods without type hints)
        **metadata: Additional metadata (read_only_hint, destructive_hint, etc.)

    Raises:
        ValueError: If method signature is missing type hints AND no manual schema provided
    """

    def decorator(f):
        # Extract metadata from function itself, with parameter overrides
        tool_name = name or f.__name__
        tool_description = description or inspect.getdoc(f) or ""

        # Warn if no docstring
        if not tool_description:
            _logger.warning(
                f"Tool '{tool_name}' has no docstring. "
                f"Add a docstring for better LLM experience."
            )

        # If manual schema provided, skip type hint validation
        if schema:
            f._llm_tool_schema = schema
        else:
            # Require type hints if no manual schema
            _validate_type_hints(f, tool_name)

        # Mark the function with metadata (for model+method lookup)
        f._is_llm_tool = True
        f._llm_tool_name = tool_name
        f._llm_tool_description = tool_description
        f._llm_tool_metadata = metadata
        f._llm_tool_xml_managed = xml_managed  # If True, skip auto-registration

        @wraps(f)
        def wrapper(*args, **kwargs):
            return f(*args, **kwargs)

        # Copy metadata to wrapper
        wrapper._is_llm_tool = f._is_llm_tool
        wrapper._llm_tool_name = f._llm_tool_name
        wrapper._llm_tool_description = f._llm_tool_description
        wrapper._llm_tool_metadata = f._llm_tool_metadata
        wrapper._llm_tool_xml_managed = f._llm_tool_xml_managed
        if hasattr(f, "_llm_tool_schema"):
            wrapper._llm_tool_schema = f._llm_tool_schema

        return wrapper

    # Support both @llm_tool and @llm_tool(schema=...)
    if func is None:
        # Called with arguments: @llm_tool(schema=...)
        return decorator
    else:
        # Called without arguments: @llm_tool
        return decorator(func)


def _validate_type_hints(func, tool_name):
    """
    Validate that a decorated method has proper type hints.

    Raises:
        ValueError: If any parameter (except 'self') is missing a type hint
    """
    sig = inspect.signature(func)

    # Check parameters
    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue

        if param.annotation == inspect.Parameter.empty:
            raise ValueError(
                f"@llm_tool decorator requires type hints.\\n"
                f"Tool '{tool_name}' parameter '{param_name}' has no type hint.\\n\\n"
                f"Fix: Add type hint like:\\n"
                f"  def {func.__name__}(self, {param_name}: str, ...) -> dict:\\n\\n"
                f"Or provide explicit schema:\\n"
                f"  @llm_tool(schema={{...}})\\n"
                f"  def {func.__name__}(self, {param_name}, ...):"
            )

    # Check return type
    if sig.return_annotation == inspect.Signature.empty:
        raise ValueError(
            f"@llm_tool decorator requires return type hint.\\n"
            f"Tool '{tool_name}' has no return type hint.\\n\\n"
            f"Fix: Add return type hint like:\\n"
            f"  def {func.__name__}(...) -> dict:"
        )


def is_llm_tool(func):
    """
    Check if a function is decorated with @llm_tool.

    Args:
        func: Function to check

    Returns:
        bool: True if function is decorated with @llm_tool
    """
    return getattr(func, "_is_llm_tool", False)


def get_tool_metadata(func):
    """
    Get metadata from a decorated function.

    Args:
        func: Decorated function

    Returns:
        dict: Tool metadata or None if not decorated
    """
    if not is_llm_tool(func):
        return None

    return {
        "name": getattr(func, "_llm_tool_name", None),
        "description": getattr(func, "_llm_tool_description", None),
        "metadata": getattr(func, "_llm_tool_metadata", {}),
        "schema": getattr(func, "_llm_tool_schema", None),
    }
