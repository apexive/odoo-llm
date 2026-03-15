{
    "name": "LLM Tool Demo",
    "version": "17.0.1.0.0",
    "category": "Productivity/LLM",
    "summary": "Demonstration of @llm_tool decorator usage",
    "description": """
LLM Tool Demo Module
====================

This module demonstrates how to create LLM tools using the @llm_tool decorator.

Features:
---------
* 6 example tools showing different decorator patterns
* Read-only, destructive, and idempotent tool examples
* Type hints and manual schema examples
* Business logic integration (CRM, Sales, Notifications)
* Best practices for tool development

Examples Included:
------------------
1. get_system_info - Simple read-only tool
2. calculate_business_days - Utility tool with type hints
3. create_lead_from_description - Business logic tool
4. generate_sales_report - Complex reporting tool
5. legacy_example - Manual schema for legacy code
6. send_notification_to_user - User interaction tool

Use this module as a reference when creating your own LLM tools.
    """,
    "author": "Apexive",
    "website": "https://github.com/apexive/odoo-llm",
    "license": "LGPL-3",
    "depends": [
        "llm_tool",
        "crm",  # For lead creation example
        "sale",  # For sales report example
        "mail",  # For notification example
    ],
    "data": [
        "security/ir.model.access.csv",
    ],
    "demo": [],
    "images": ["static/description/banner.jpeg"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
