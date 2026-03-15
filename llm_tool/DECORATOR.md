# @llm_tool Decorator Guide

## Overview

The `@llm_tool` decorator makes any Python method available as an LLM tool with **automatic registration** - no XML needed!

## Basic Usage

```python
from odoo import models
from odoo.addons.llm_tool.decorators import llm_tool

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @llm_tool
    def create_sales_quote(self, customer: str, amount: float) -> dict:
        """Create a sales quotation for a customer"""
        # Your implementation here
        return {"quote_id": 123, "status": "draft"}
```

**That's it!** The tool is automatically registered in the database when Odoo loads.

**How it works:**

1. Decorator marks the method at import time
2. `_register_hook()` scans all models for marked methods
3. Automatically creates/updates `llm.tool` records
4. Tool becomes available to LLM providers (Claude, GPT, etc.)

## What the Decorator Does

**At decoration time (import):**

```python
@llm_tool
def my_tool(x: int) -> str:
    """My tool"""
    pass

# Sets Python attributes:
# my_tool._is_llm_tool = True
# my_tool._llm_tool_name = "my_tool"
# my_tool._llm_tool_description = "My tool"
```

**At registry load (`_register_hook()`):**

- Scans all models for methods with `_is_llm_tool = True`
- Creates database records for auto-registered functions

## Usage Patterns

### With Type Hints (Recommended)

```python
@llm_tool
def my_tool(self, name: str, count: int = 10) -> dict:
    """Tool description here"""
    pass
```

### Without Type Hints (Legacy)

```python
@llm_tool(schema={
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "count": {"type": "integer"}
    }
})
def my_tool(self, name, count):
    """Tool description here"""
    pass
```

### With Metadata

```python
@llm_tool(read_only_hint=True)
def get_data(self, id: int) -> dict:
    """Get data by ID"""
    pass
```

## Auto-Registration Details

**When a function is decorated:**

1. Decorator marks it with `_is_llm_tool = True`
2. Stores name, description from function itself
3. No database access yet

**When Odoo loads (`_register_hook()`):**

1. Scans all models for `_is_llm_tool` marked methods
2. Creates/updates database record:
   ```python
   {
       'name': method._llm_tool_name,
       'implementation': 'function',
       'description': method._llm_tool_description,
       'decorator_model': model_name,
       'decorator_method': method.__name__,
       # Plus any metadata: read_only_hint, idempotent_hint, etc.
   }
   ```
3. If manual schema provided via `schema=` parameter, stores it in `input_schema` field
4. Updates existing records if metadata changed (only if `auto_update=True`)
5. Logs registration success for debugging

**Note on `auto_update` field:**

- New tools default to `auto_update=True` - decorator changes automatically applied
- Set to `False` in UI to manually manage a tool's metadata
- Useful when testing: change decorator → restart → see changes (with `auto_update=True`)
- Useful for customization: set `auto_update=False` → edit in UI → changes persist

## Why Use This?

✅ **Zero boilerplate** - No XML records needed
✅ **DRY principle** - Single source of truth (docstring)
✅ **Pythonic** - Uses standard Python patterns
✅ **Type-safe** - Optional type hints for validation
✅ **Auto-sync** - Database always matches code
✅ **Odoo pattern** - Same as `@api.constrains`, `@api.model`

## Performance Considerations

### Scanning Approach

**Current Implementation (Simple):**

```python
# In _register_hook()
for model_name in self.env.registry:  # ~100 models
    model = self.env[model_name]
    for attr_name in dir(model):  # ~100 methods per model
        method = getattr(model, attr_name, None)
        if getattr(method, '_is_llm_tool', False):  # Fast attribute check
            self._register_function_tool(model_name, attr_name, method)
```

**Performance:**

- Scans ~5,000-10,000 methods once at startup
- Takes milliseconds (attribute checks are very fast)
- Happens once when registry loads, not on every request
- Negligible compared to normal Odoo startup operations

**Alternative: Registry Pattern (Faster)**

```python
# In decorators.py - maintain a global registry
_DECORATED_TOOLS = []

def llm_tool(func):
    func._is_llm_tool = True
    _DECORATED_TOOLS.append(func)  # Store reference
    return func

# In _register_hook() - only iterate registered tools
for func in _DECORATED_TOOLS:
    # Only ~10-20 iterations instead of ~10,000
    self._register_function_tool(func)
```

**Trade-off:**

- Current: Simpler code, no global state, slightly slower (still fast)
- Registry: Faster scan, but requires global state management

**Recommendation:** Start with current approach (simple). Optimize only if needed.

## That's All You Need!

The decorator just marks methods. All the heavy lifting (schema generation, validation, execution) happens at runtime.
