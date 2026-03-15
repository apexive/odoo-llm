# LLM Tool Demo

Demonstration module showing how to create LLM tools using the `@llm_tool` decorator.

**Module Type:** 📖 Demo/Tutorial (Tool Development)

## Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                     Consumers of Tools                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │
│  │llm_assistant│  │  llm_letta  │  │   llm_mcp_server    │   │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘   │
└─────────┼────────────────┼────────────────────┼──────────────┘
          └────────────────┼────────────────────┘
                           ▼
              ┌───────────────────────────────────────────┐
              │              llm_tool                     │
              │         (Tool Framework)                  │
              └─────────────────────┬─────────────────────┘
                                    │
                                    ▼
              ┌───────────────────────────────────────────┐
              │     ★ llm_tool_demo (This Module) ★       │
              │         Example Tool Implementations       │
              │  📖 6 Examples │ Best Practices │ Learn   │
              └─────────────────────┬─────────────────────┘
                                    │
                                    ▼
              ┌───────────────────────────────────────────┐
              │                   llm                     │
              │            (Core Base Module)             │
              └───────────────────────────────────────────┘
```

## Installation

### What to Install

**For learning tool development:**

```bash
odoo-bin -d your_db -i llm_tool_demo
```

### Auto-Installed Dependencies

- `llm` (core infrastructure)
- `llm_tool` (tool framework)

### What You'll Learn

| Feature             | Example                           |
| ------------------- | --------------------------------- |
| **Read-only tools** | `get_system_info`                 |
| **Utility tools**   | `calculate_business_days`         |
| **CRM tools**       | `create_lead_from_description`    |
| **Reporting**       | `generate_sales_report`           |
| **Legacy code**     | `get_record_info` (manual schema) |
| **Notifications**   | `send_notification_to_user`       |

## Overview

This module contains **6 example tools** that demonstrate different patterns and best practices for creating LLM-callable tools in Odoo.

**Key Feature**: Tools are organized in **realistic file structure** - each tool inherits the appropriate model it extends (CRM, Sales, Users, etc.)

## Module Structure

```
llm_tool_demo/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── crm_lead.py          # CRM lead creation tool
│   ├── sale_order.py        # Sales reporting tool
│   ├── res_users.py         # User notification + system info tools
│   ├── ir_model.py          # Record inspection tool (legacy example)
│   └── utility_tools.py     # Generic utility tools (TransientModel)
└── README.md
```

**Why this structure?**

- ✅ **Realistic**: Mirrors real-world Odoo development patterns
- ✅ **Organized**: Each file extends the model it works with
- ✅ **Maintainable**: Easy to find and update tools
- ✅ **Best Practice**: Follows Odoo's inheritance patterns

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install the module
odoo-bin -d your_database -i llm_tool_demo
```

The tools will be **automatically registered** in the `llm.tool` model when the module loads.

## Demo Tools

### 1. `get_system_info` - Simple Read-Only Tool

**Location**: `models/res_users.py` (inherits `res.users`)

**Purpose**: Get basic Odoo system information

**Features**:

- ✅ Read-only operation
- ✅ Idempotent (can be called multiple times safely)
- ✅ No parameters required

**Example Usage**:

```python
users_model = env['res.users']
result = users_model.get_system_info()
# Returns: {
#     "database_name": "production",
#     "odoo_version": "18.0",
#     "company_name": "My Company",
#     ...
# }
```

**Decorator**:

```python
@llm_tool(read_only_hint=True, idempotent_hint=True)
def get_system_info(self) -> dict:
    """Get basic Odoo system information..."""
```

---

### 2. `calculate_business_days` - Utility Tool

**Location**: `models/utility_tools.py` (TransientModel `llm.utility.tools`)

**Purpose**: Calculate business days between two dates

**Features**:

- ✅ Type hints for automatic schema generation
- ✅ Optional parameters with defaults
- ✅ Input validation and error handling
- ✅ Uses TransientModel for stateless utility functions

**Example Usage**:

```python
utility_tools = env['llm.utility.tools']
result = utility_tools.calculate_business_days(
    start_date='2024-01-01',
    end_date='2024-01-31',
    exclude_weekends=True
)
# Returns: {
#     "total_days": 31,
#     "business_days": 23,
#     "weekend_days": 8,
#     ...
# }
```

**Decorator**:

```python
@llm_tool(read_only_hint=True, idempotent_hint=True)
def calculate_business_days(
    self, start_date: str, end_date: str, exclude_weekends: bool = True
) -> dict:
    """Calculate the number of business days between two dates..."""
```

---

### 3. `create_lead_from_description` - Business Logic Tool

**Location**: `models/crm_lead.py` (inherits `crm.lead`)

**Purpose**: Create CRM leads from natural language descriptions

**Features**:

- ⚠️ Destructive operation (creates records)
- ✅ Integrates with Odoo CRM module
- ✅ AI-friendly (designed for LLM input)
- ✅ Extends the model it works with (best practice)

**Example Usage**:

```python
lead_model = env['crm.lead']
result = lead_model.create_lead_from_description(
    description="Interested in purchasing 100 units of Product X for Q2 2024",
    contact_name="John Smith",
    email="john@example.com",
    phone="+1-555-0123"
)
# Returns: {
#     "lead_id": 42,
#     "lead_name": "Interested in purchasing 100 units...",
#     "contact_name": "John Smith",
#     ...
# }
```

**Decorator**:

```python
@llm_tool(destructive_hint=True)
def create_lead_from_description(
    self, description: str, contact_name: str = "", email: str = "", phone: str = ""
) -> dict:
    """Create a CRM lead from a natural language description..."""
```

---

### 4. `generate_sales_report` - Complex Reporting Tool

**Location**: `models/sale_order.py` (inherits `sale.order`)

**Purpose**: Generate sales statistics for a date range

**Features**:

- ✅ Read-only operation
- ✅ Complex data aggregation
- ✅ Top N results (configurable limit)
- ✅ Extends sale.order for sales-specific logic

**Example Usage**:

```python
sale_model = env['sale.order']
result = sale_model.generate_sales_report(
    start_date='2024-01-01',
    end_date='2024-03-31',
    limit=5
)
# Returns: {
#     "total_orders": 150,
#     "total_revenue": 250000.00,
#     "average_order_value": 1666.67,
#     "top_customers": [
#         {"name": "ACME Corp", "revenue": 50000.00, "order_count": 10},
#         ...
#     ]
# }
```

**Decorator**:

```python
@llm_tool(read_only_hint=True)
def generate_sales_report(
    self, start_date: str, end_date: str, limit: int = 10
) -> dict:
    """Generate a sales summary report for a date range..."""
```

---

### 5. `get_record_info` - Legacy Code Example

**Location**: `models/ir_model.py` (inherits `ir.model`)

**Purpose**: Demonstrate manual schema for code without type hints

**Features**:

- ✅ Manual JSON schema definition
- ✅ Works with existing untyped code
- ✅ Backward compatibility pattern
- ✅ Shows how to add tools to system models

**Example Usage**:

```python
model_model = env['ir.model']
result = model_model.get_record_info(
    model_name='res.partner',
    record_id=1
)
# Returns: {
#     "model": "res.partner",
#     "id": 1,
#     "display_name": "My Company",
#     "name": "My Company",
#     ...
# }
```

**Decorator**:

```python
@llm_tool(
    schema={
        "type": "object",
        "properties": {
            "model_name": {
                "type": "string",
                "description": "Technical name of the Odoo model"
            },
            "record_id": {
                "type": "integer",
                "description": "ID of the record to retrieve"
            }
        },
        "required": ["model_name", "record_id"]
    },
    read_only_hint=True
)
def get_record_info(self, model_name, record_id):
    """Get basic information about any Odoo record..."""
```

---

### 6. `send_notification_to_user` - User Interaction Tool

**Location**: `models/res_users.py` (inherits `res.users`)

**Purpose**: Send in-app notifications to users

**Features**:

- ⚠️ Non-destructive but not idempotent (creates each time)
- ✅ User communication
- ✅ Notification type validation
- ✅ Logical placement in res.users model

**Example Usage**:

```python
users_model = env['res.users']
result = users_model.send_notification_to_user(
    user_id=2,
    title="Task Completed",
    message="Your sales report has been generated successfully.",
    notification_type="success"
)
# Returns: {
#     "success": True,
#     "user_id": 2,
#     "user_name": "Admin",
#     ...
# }
```

**Decorator**:

```python
@llm_tool(destructive_hint=False, idempotent_hint=False)
def send_notification_to_user(
    self, user_id: int, title: str, message: str, notification_type: str = "info"
) -> dict:
    """Send an in-app notification to a specific user..."""
```

---

## Key Concepts Demonstrated

### 1. **Automatic Registration**

All tools are automatically registered in the database via `_register_hook()`. No XML records needed!

### 2. **Type Hints for Schema Generation**

Tools with proper type hints automatically generate JSON schemas:

```python
def my_tool(self, name: str, count: int = 10) -> dict:
```

### 3. **Manual Schema for Legacy Code**

Use `schema=` parameter for existing code without type hints:

```python
@llm_tool(schema={...})
def legacy_method(self, param1, param2):
```

### 4. **Metadata Hints**

Help LLMs understand tool characteristics:

- `read_only_hint=True` - Tool doesn't modify data
- `idempotent_hint=True` - Safe to call multiple times
- `destructive_hint=True` - Modifies/creates/deletes data
- `open_world_hint=True` - Interacts with external entities

### 5. **Error Handling**

Proper validation and error messages:

```python
if not valid:
    raise UserError(_("Clear error message"))
```

### 6. **Return Values**

Always return dictionaries with meaningful keys:

```python
return {
    "success": True,
    "data": result,
    "metadata": {...}
}
```

## Testing Your Tools

### Via Python/ORM

```python
# In odoo shell
users_model = env['res.users']
result = users_model.get_system_info()
print(result)
```

### Via LLM Tool Interface

```python
# Get the registered tool
tool = env['llm.tool'].search([('name', '=', 'get_system_info')])

# Execute via tool interface
result = tool.execute({})
print(result)
```

### Via MCP Server

If you have `llm_mcp_server` installed, the tools are automatically available to Claude Desktop, Cursor, and other MCP clients.

### Via Letta Agents

If you have `llm_letta` installed, the tools can be assigned to Letta agents for use in conversations.

## File Organization - Best Practices

### Where to Put Your Tools

**Rule of Thumb**: Add tools to the model they work with!

| Tool Purpose       | Model to Inherit      | Example                   |
| ------------------ | --------------------- | ------------------------- |
| CRM operations     | `crm.lead`            | `models/crm_lead.py`      |
| Sales reporting    | `sale.order`          | `models/sale_order.py`    |
| User operations    | `res.users`           | `models/res_users.py`     |
| Partner operations | `res.partner`         | `models/res_partner.py`   |
| Generic utilities  | TransientModel        | `models/utility_tools.py` |
| System operations  | `ir.model` or similar | `models/ir_model.py`      |

### Why This Matters

**✅ Good** (Realistic - this module):

```python
# models/crm_lead.py
class CrmLead(models.Model):
    _inherit = 'crm.lead'

    @llm_tool
    def create_lead_from_description(self, description: str) -> dict:
        # Uses self.create() naturally
        lead = self.create({'name': description})
```

**❌ Bad** (Monolithic):

```python
# models/all_tools.py
class AllTools(models.Model):
    _name = 'all.tools'

    @llm_tool
    def create_lead_from_description(self, description: str) -> dict:
        # Has to use env['crm.lead'].create() - awkward!
        lead = self.env['crm.lead'].create({'name': description})
```

### Benefits of Proper Organization

1. **Natural API**: Use `self.create()`, `self.search()` directly
2. **Logical grouping**: CRM tools in CRM files, Sales tools in Sales files
3. **Easy to find**: Know exactly where to look
4. **Separation of concerns**: Each file has a clear purpose
5. **Odoo convention**: Follows standard Odoo module patterns

## Best Practices

1. ✅ **Inherit the right model** - Add tools to the model they work with
2. ✅ **Use descriptive docstrings** - They become the tool description for LLMs
3. ✅ **Add type hints** - Automatic schema generation is cleaner
4. ✅ **Set appropriate hints** - Help LLMs use tools correctly
5. ✅ **Validate inputs** - Raise clear UserError messages
6. ✅ **Return structured data** - Dictionaries with clear keys
7. ✅ **Handle errors gracefully** - Don't let exceptions bubble unexpectedly
8. ✅ **Separate by concern** - One file per model inheritance

## Creating Your Own Tools

```python
from odoo import models
from odoo.addons.llm_tool.decorators import llm_tool

class MyModel(models.Model):
    _name = 'my.model'

    @llm_tool(read_only_hint=True)
    def my_custom_tool(self, param1: str, param2: int = 5) -> dict:
        """Brief description of what this tool does

        Longer description with more details about parameters
        and expected behavior.

        Args:
            param1: Description of param1
            param2: Description of param2 (default: 5)

        Returns:
            Dictionary with results
        """
        # Your implementation
        return {"result": "success"}
```

That's it! The tool will be automatically registered when Odoo loads.

## Troubleshooting

### Tool Not Appearing in Database

Check the logs for registration errors:

```bash
grep "llm.tool" odoo.log
```

### Schema Generation Issues

If using type hints fails, provide manual schema:

```python
@llm_tool(schema={...})
def my_tool(self, param):
    pass
```

### Method Not Found

Ensure:

1. Module is properly installed
2. Model is inherited correctly
3. Method is not private (doesn't start with `_`)

## Learn More

- **Decorator Guide**: See `llm_tool/DECORATOR.md` for detailed decorator documentation
- **Tool System**: See `llm_tool/README.md` for overall tool system architecture
- **MCP Integration**: See `llm_mcp_server/README.md` for Claude Desktop integration
- **Letta Integration**: See `llm_letta/README.md` for AI agent integration

## License

LGPL-3

## Author

Apexive - https://apexive.com
