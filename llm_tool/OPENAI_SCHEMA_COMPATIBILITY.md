# OpenAI Schema Compatibility Guide

This document outlines the limitations and incompatibilities between Pydantic-generated JSON schemas and OpenAI's Structured Outputs / Function Calling API.

## The Problem

OpenAI's Function Calling and Structured Outputs only support a **tiny subset of JSON Schema**, while Pydantic generates rich, full-featured schemas that use the complete JSON Schema specification.

## Key Incompatibilities

### 1. Optional Fields with Defaults

**Problem:**

```python
# Pydantic generates:
"age": {"type": ["integer", "null"], "minimum": 0, "maximum": 120, "default": null}

# OpenAI expects:
"age": {"type": ["integer", "null"]}  # No 'default' field allowed!
```

**Solution:**

- Make all fields required in the schema
- Use nullable types `["type", "null"]` for optional values
- Remove the `default` key from the schema

### 2. Numeric Constraints Are Not Supported

**Problem:**

```python
age: int = Field(ge=0, le=120)  # minimum/maximum not supported by OpenAI
```

**Solution:**

- Remove `minimum`, `maximum`, `exclusiveMinimum`, `exclusiveMaximum` from schema
- Document constraints in the field description
- Validate constraints in application code after receiving the response

### 3. Recursive Models Are Impossible

**Problem:**

```python
class TreeNode(BaseModel):
    value: str
    children: List['TreeNode'] = []  # OpenAI doesn't support $ref or recursion
```

**Solution:**

- OpenAI doesn't support `$ref` at all - no recursive schemas, period
- Redesign to use flat structures:
  ```python
  class TreeNode(BaseModel):
      id: str
      value: str
      parent_id: Optional[str] = None
      child_ids: List[str] = []
  ```
- Or limit to fixed depth with different model types

### 4. The `additionalProperties` Trap

**Problem:**

```python
settings: dict  # Generates {"type": "object", "additionalProperties": {}}

# Empty schema in additionalProperties causes OpenAI to fail
```

**Solution:**

- Set `"additionalProperties": false` OR
- Provide a proper type: `"additionalProperties": {"type": "string"}`
- Never use empty schema `{}`

### 5. Union Types with `anyOf` Are Forbidden

**Problem:**

```python
result: Union[str, int, float]  # anyOf not supported in strict mode
```

**Solution:**

- Simplify unions to single types where possible
- Use string enums for predefined choices
- For truly polymorphic data, consider using discriminated unions or separate fields

### 6. String Format Constraints

**Problem:**

```python
# Pydantic generates:
"created_at": {"type": "string", "format": "date-time"}  # format not supported
```

**Solution:**

- Remove `format` field from schema
- Document expected format in description
- Validate format in application code

## Best Practices for LLM Tools

### 1. Keep Schemas Simple

- Prefer flat structures over nested ones
- Use primitives (str, int, bool, float, None) when possible
- Avoid deeply nested objects

### 2. Handle Complex Data

For complex nested structures (like Odoo domains):

```python
# Option A: Use JSON strings
domain: str = Field(description="JSON-encoded domain like [[\"field\", \"=\", \"value\"]]")

# Then parse:
actual_domain = json.loads(domain)
```

### 3. Document Constraints

```python
age: int = Field(
    description="User age in years. Must be between 0 and 120 (validated server-side)"
)
```

### 4. Make Everything Required

```python
# Instead of:
name: Optional[str] = None

# Use:
name: Union[str, None]  # Required field that can be null
```

### 5. Test Schema Generation

Always validate your schema:

```python
schema = MyModel.model_json_schema()
# Check for:
# - No 'default' keys
# - No 'minimum'/'maximum'
# - No empty 'additionalProperties: {}'
# - No 'anyOf' in strict mode
# - No '$ref' (recursive models)
```

## Tools Migration Strategy

When migrating existing tools to be OpenAI-compatible:

1. **Audit the schema:** Generate and inspect `model_json_schema()`
2. **Override if needed:** Use custom `get_input_schema()` method
3. **Simplify types:** Remove recursive models, complex unions
4. **Document constraints:** Move validation rules to descriptions
5. **Validate server-side:** Check constraints after LLM response

## References

- [Medium Article: How to Fix OpenAI Structured Outputs Breaking Your Pydantic Models](https://medium.com/@aviadr1/how-to-fix-openai-structured-outputs-breaking-your-pydantic-models-bdcd896d43bd)
- [GitHub Issue: Pydantic conversion logic for structured outputs is broken for dictionaries](https://github.com/openai/openai-python/issues/2004)
- [OpenAI Structured Outputs Documentation](https://platform.openai.com/docs/guides/structured-outputs)

## Common Errors

### Error: `'default' is not allowed`

Remove `default` from schema or make field required with nullable type.

### Error: `'additionalProperties' is not false`

Set `additionalProperties: false` or provide explicit type.

### Error: `anyOf is not supported in strict mode`

Simplify union types or use separate fields.

### Error: `$ref not supported`

Remove recursive model definitions, use flat structures with IDs.
