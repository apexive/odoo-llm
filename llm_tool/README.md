# LLM Tool

**AI Function Calling for Odoo** - Enable LLMs (ChatGPT, Claude, etc.) to interact with your Odoo database by calling tools/functions.

**Module Type:** 📦 Infrastructure

![Architecture](static/description/llm_tool_architecture.png)

## Installation

### What to Install

This module is typically **auto-installed** as a dependency of `llm_assistant` or `llm_thread`.

**For AI with function calling:**

```
llm_assistant + llm_openai (or other provider)
```

### Auto-Installed Dependencies

These are pulled in automatically:

- `llm` (core infrastructure)

### Optional Enhancements

| Module                 | Adds                          |
| ---------------------- | ----------------------------- |
| `llm_tool_demo`        | 6 example tools to learn from |
| `llm_tool_knowledge`   | RAG search tool for LLMs      |
| `llm_tool_ocr_mistral` | OCR tool using Mistral        |

### Common Setups Using This Module

| I want to...                    | Install                                         |
| ------------------------------- | ----------------------------------------------- |
| AI that can search Odoo records | `llm_assistant` + `llm_openai` (tools included) |
| AI that can search documents    | Above + `llm_knowledge` + `llm_tool_knowledge`  |
| Expose tools to Claude Desktop  | Above + `llm_mcp_server`                        |
| Learn to build custom tools     | `llm_tool_demo`                                 |

## Quick Start for Developers

There are **two ways** to create tools for LLMs:

### 1. Using the `@llm_tool` Decorator (Recommended)

**Zero boilerplate** - just decorate your method and it's automatically available to LLMs.

```python
from odoo import models
from odoo.addons.llm_tool.decorators import llm_tool

class ResUsers(models.Model):
    _inherit = "res.users"

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def get_system_info(self) -> dict:
        """Get basic Odoo system information"""
        return {
            "database_name": self.env.cr.dbname,
            "company_name": self.env.company.name,
            "user_count": self.env["res.users"].search_count([]),
        }
```

**That's it!** The tool is automatically:

- ✅ Registered in the database when Odoo starts
- ✅ Available to all LLM providers (Claude, ChatGPT, etc.)
- ✅ Description extracted from docstring
- ✅ Schema generated from type hints
- ✅ Validated with Pydantic

#### Decorator Options

```python
@llm_tool(
    schema={...},              # Optional: Manual JSON schema (if no type hints)
    read_only_hint=True,       # Tool only reads data
    idempotent_hint=True,      # Multiple calls have same effect
    destructive_hint=False,    # Tool modifies/deletes data
    open_world_hint=False,     # Tool interacts with external systems
)
def your_tool_method(self, param1: str, param2: int = 10) -> dict:
    """Tool description - shown to the LLM"""
    pass
```

#### More Examples

**With Parameters:**

```python
@llm_tool(destructive_hint=True)
def create_lead_from_description(
    self,
    description: str,
    contact_name: str = "",
    email: str = ""
) -> dict:
    """Create a CRM lead from a natural language description"""
    lead = self.env["crm.lead"].create({
        "name": description[:100],
        "description": description,
        "contact_name": contact_name,
        "email_from": email,
    })
    return {"lead_id": lead.id, "name": lead.name}
```

**Manual Schema (for methods without type hints):**

```python
@llm_tool(
    schema={
        "type": "object",
        "properties": {
            "model_name": {"type": "string"},
            "record_id": {"type": "integer"},
        },
        "required": ["model_name", "record_id"],
    },
    read_only_hint=True,
)
def get_record_info(self, model_name, record_id):
    """Get information about any Odoo record"""
    record = self.env[model_name].browse(record_id)
    return {
        "id": record.id,
        "display_name": record.display_name,
        "model": model_name,
    }
```

**See `llm_tool_demo` module for 6 complete examples.**

---

### 2. Using Custom Implementation (Traditional Odoo Way)

For tools that should be managed via XML data files (more Odoo-native approach), extend `llm.tool` and implement `{implementation}_execute`:

```python
class LLMTool(models.Model):
    _inherit = "llm.tool"

    @api.model
    def _get_available_implementations(self):
        implementations = super()._get_available_implementations()
        implementations.append(("my_custom_tool", "My Custom Tool"))
        return implementations

    def my_custom_tool_execute(self, param1, param2=None):
        """Execute your custom tool logic"""
        # Your implementation here
        return {"result": "success"}
```

Then create tool records in XML:

```xml
<record id="my_custom_tool" model="llm.tool">
    <field name="name">my_custom_tool</field>
    <field name="implementation">my_custom_tool</field>
    <field name="description">Tool description for the LLM</field>
    <field name="input_schema">{"type": "object", "properties": {...}}</field>
</record>
```

**Benefits of this approach:**

- Tools defined in XML data files (traditional Odoo pattern)
- Tool descriptions and schemas managed in XML
- Better for tools that don't map to a single model method

**Built-in implementations:**

- `odoo_record_retriever` - Search and retrieve Odoo records
- `odoo_record_creator` - Create new records
- `odoo_record_updater` - Update existing records
- `odoo_record_unlinker` - Delete records
- `odoo_model_method_executor` - Execute any model method
- `odoo_model_inspector` - Inspect model structure and fields

See `llm_tool/data/llm_tool_data.xml` for complete examples.

---

## How Tools Work

1. **LLM Receives Tool Definitions** - When chatting, the LLM gets a list of available tools with their schemas
2. **LLM Decides to Call Tool** - Based on user request, LLM chooses which tool to call with what parameters
3. **Odoo Executes Tool** - Parameters are validated and the tool method is executed
4. **Result Returned to LLM** - Tool output is sent back to the LLM to formulate a response

## Tool Registration

**Decorated tools** are automatically registered when Odoo starts via `_register_hook()`. If you:

- Add a new `@llm_tool` decorated method → Automatically registered on next restart
- Remove a decorated method → Automatically deactivated
- Change method signature → Schema automatically regenerated

**Auto-update behavior:**

- By default, decorated tools are auto-updated on every Odoo restart
- To manually manage a tool's metadata, set `auto_update=False` in the UI
- When `auto_update=False`, decorator changes won't overwrite your manual edits

**Manual tools** are registered via XML data files and persist across restarts.

## Tool Security

```python
requires_user_consent = True   # User must approve before execution
read_only_hint = True          # Tool only reads, doesn't modify
destructive_hint = True        # Tool may modify/delete data
```

Configure consent rules in: **LLM → Configuration → Tool Consent Configs**

## Testing Your Tools

```python
# In Odoo shell or tests
tool = env["llm.tool"].search([("name", "=", "your_tool_name")])
result = tool.execute({"param1": "value1", "param2": 42})
print(result)
```

Or use the demo module's tests as examples:

- `llm_tool/tests/` - Core functionality tests
- `llm_tool_demo/tests/` - Decorator and execution tests

## Related Modules

- **`llm`** - Base LLM infrastructure
- **`llm_thread`** - Chat interface with tool execution
- **`llm_assistant`** - Configure assistants with specific tools
- **`llm_tool_demo`** - Example tools using `@llm_tool` decorator
- **`llm_mcp_server`** - Expose tools via Model Context Protocol

## Documentation

- [Decorator Guide](DECORATOR.md) - Detailed decorator documentation
- [Changelog](changelog.rst) - Version history
- [GitHub Repository](https://github.com/apexive/odoo-llm)

## License

LGPL-3 - See LICENSE file for details.

---

_© 2025 Apexive Solutions LLC_
