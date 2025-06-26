{
    "name": "LLM Assistant",
    "summary": """
        LLM/AI Assistant module for Odoo
    """,
    "description": """
Assistantic AI (LLM) Assistant for Odoo
==================
Configure AI assistants with specific roles, goals, and tools to enhance your AI interactions.

Key Features:
- Create and configure AI assistants with specific roles and goals
- Assign preferred tools to each assistant
- Automatically generate system prompts based on assistant configuration
- Attach assistants to chat threads for consistent behavior
- Full integration with the LLM chat system
- Support for text, YAML, and JSON prompt templates

Use cases include creating specialized assistants for customer support, data analysis, training assistance, and more.
    """,
    "category": "Productivity, Discuss",
    "version": "16.0.1.1.0",
    "depends": [
        "base",
        "mail",
        "web",
        "llm",
        "llm_thread",
        "llm_tool",
        "llm_prompt",
        "web_json_editor",
    ],
    "author": "Apexive Solutions LLC",
    "website": "https://github.com/apexive/odoo-llm",
    "data": [
        "security/ir.model.access.csv",
        "data/llm_prompt_data.xml",
        "data/llm_assistant_data.xml",
        "views/llm_assistant_views.xml",
        "views/llm_thread_views.xml",
        "views/llm_menu_views.xml",
    ],
    "images": [
        "static/description/banner.jpeg",
    ],
    "assets": {
        "web.assets_backend": [
            "llm_assistant/static/src/models/main.js",
            # Models
            "llm_assistant/static/src/models/llm_assistant.js",
            "llm_assistant/static/src/models/llm_chat.js",
            "llm_assistant/static/src/models/thread.js",
            "llm_assistant/static/src/models/llm_chat_thread_header_view.js",
            # Components
            "llm_assistant/static/src/components/llm_chat_thread_header/llm_chat_thread_header.js",
            "llm_assistant/static/src/components/llm_chat_thread_header/llm_chat_thread_header.xml",
        ],
    },
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
