This technical module provides the function-calling layer for the LLM
integration: it defines what a *tool* is, how one is registered, how its
input schema is derived, and how it is executed.

A tool is an `llm.tool` record bound to a Python method. Records reach the
database two ways:

- **Decorator.** A model method marked with `@llm_tool` is discovered at
  startup by `_register_hook()`, which scans the registry and syncs what it
  finds to `llm_tool` via raw SQL under a PostgreSQL advisory lock, so only one
  worker writes. The decorator requires type hints on every parameter and on
  the return value, and the input schema is generated from that signature.
- **XML.** An `llm.tool` record declared in a data file, for cases where the
  definition should be under the module's control rather than the scanner's.
  A decorated method marked `xml_managed=True` is skipped by the scanner.

Tool definitions are emitted in Model Context Protocol form, so the same
definition serves an in-Odoo chat thread and an external MCP client.

The module also ships six generic tools that operate on any model the calling
user may access: record retrieval, creation, update and deletion, arbitrary
model-method execution, and model introspection.
