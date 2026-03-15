==========================================
LLM Tool Demo Module
==========================================

Learn how to create LLM tools with examples.

**Module Type:** 📖 Demo/Tutorial (Tool Development)

Architecture
============

::

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

Installation
============

What to Install
---------------

**For learning tool development:**

.. code-block:: bash

    odoo-bin -d your_db -i llm_tool_demo

Auto-Installed Dependencies
---------------------------

- ``llm`` (core infrastructure)
- ``llm_tool`` (tool framework)

What You'll Learn
-----------------

+---------------------+--------------------------------+
| Feature             | Example                        |
+=====================+================================+
| **Read-only tools** | ``get_system_info``            |
+---------------------+--------------------------------+
| **Utility tools**   | ``calculate_business_days``    |
+---------------------+--------------------------------+
| **CRM tools**       | ``create_lead_from_description``|
+---------------------+--------------------------------+
| **Reporting**       | ``generate_sales_report``      |
+---------------------+--------------------------------+
| **Legacy code**     | ``get_record_info`` (manual)   |
+---------------------+--------------------------------+
| **Notifications**   | ``send_notification_to_user``  |
+---------------------+--------------------------------+

Demo Tools
==========

1. get_system_info
------------------

**Location**: ``models/res_users.py``

Simple read-only tool to get Odoo system information.

.. code-block:: python

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def get_system_info(self) -> dict:
        """Get basic Odoo system information..."""

2. calculate_business_days
--------------------------

**Location**: ``models/utility_tools.py``

Utility tool with type hints for automatic schema generation.

3. create_lead_from_description
-------------------------------

**Location**: ``models/crm_lead.py``

Business logic tool that creates CRM leads (destructive operation).

4. generate_sales_report
------------------------

**Location**: ``models/sale_order.py``

Complex reporting tool with data aggregation.

5. get_record_info
------------------

**Location**: ``models/ir_model.py``

Legacy code example with manual JSON schema.

6. send_notification_to_user
----------------------------

**Location**: ``models/res_users.py``

User interaction tool for in-app notifications.

Key Concepts
============

Type Hints for Schema Generation
--------------------------------

.. code-block:: python

    def my_tool(self, name: str, count: int = 10) -> dict:
        ...

Metadata Hints
--------------

- ``read_only_hint=True`` - Doesn't modify data
- ``idempotent_hint=True`` - Safe to call multiple times
- ``destructive_hint=True`` - Modifies/creates/deletes data

Technical Specifications
========================

- **Version**: 18.0.1.0.0
- **License**: LGPL-3
- **Dependencies**: ``llm``, ``llm_tool``, ``crm``, ``sale``

Related Modules
===============

- **``llm_tool``** - Tool framework (required reading)
- **``llm_mcp_server``** - MCP integration
- **``llm_letta``** - Letta agent integration

License
=======

LGPL-3

----

*© 2025 Apexive Solutions LLC*
