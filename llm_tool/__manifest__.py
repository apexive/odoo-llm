{
    "name": "LLM Tool",
    "version": "18.0.4.1.2",
    "category": "Technical",
    "summary": "Function calling and tool execution for LLM models to interact with Odoo",
    "description": """
        Automate Your Odoo Database with AI Assistants & Chat AI | ChatGPT, Grok, Anthropic, DeepSeek

        Boost your Odoo database automation with AI-powered assistants using ChatGPT, Grok, Anthropic, and DeepSeek. Streamline
        workflows, optimize data management, and enhance productivity with AI tools seamlessly integrated into your Odoo
        instance. This module provides a robust framework for integrating Large Language Models (LLMs) with Odoo, enabling
        intelligent interactions through configurable tools. Key features include:

        - Function Calling: Enable AI models to call specific functions based on user requests
        - Definition and management of LLM tools with custom implementations
        - Support for dynamic schema generation from Pydantic models
        - Flexible override options for tool descriptions and schemas
        - Integration with Odoo mail threads for chat-like interactions with AI assistants
        - Extensible architecture for adding new tool implementations

        Perfect for businesses looking to leverage AI-driven ERP management, this module empowers administrators to create,
        configure, and customize LLM tools, supporting intelligent Odoo assistants that automate workflows and enhance business
        automation.
    """,
    "author": "Apexive Solutions LLC",
    "website": "https://github.com/apexive/odoo-llm",
    "license": "LGPL-3",
    "depends": ["base", "mail", "llm"],
    "external_dependencies": {
        "python": ["pydantic>=2.0.0", "mcp"],
    },
    "data": [
        "security/ir.model.access.csv",
        "views/llm_tool_views.xml",
        "views/llm_tool_consent_config_views.xml",
        "data/llm_tool_data.xml",
        "data/llm_tool_consent_config_data.xml",
        "data/server_actions.xml",
        "views/llm_menu_views.xml",
    ],
    "images": [
        "static/description/banner.jpeg",
    ],
    "auto_install": False,
    "application": False,
    "installable": True,
}
