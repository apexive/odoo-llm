{
    "name": "LLM Prompt Templates",
    "summary": """
        Create and manage reusable prompt templates for LLM interactions""",
    "description": """
        This module extends the LLM integration base to support:
        - Creating reusable prompt templates in text, YAML, or JSON format
        - Dynamic arguments within prompts
        - Multi-step prompt workflows through structured formats
        - Prompt discovery and retrieval
        - Categories and tags for organization
        - Enhanced prompt testing with context simulation
        - Related record integration for prompt testing
    """,
    "author": "Apexive Solutions LLC",
    "website": "https://github.com/apexive/odoo-llm",
    "category": "Technical",
    "version": "16.0.1.3.0",
    "depends": ["llm", "llm_thread"],
    "external_dependencies": {
        "python": ["jinja2", "pyyaml"],
    },
    "data": [
        "security/ir.model.access.csv",
        "data/llm_prompt_tag_data.xml",
        "data/llm_prompt_category_data.xml",
        "data/llm_prompt_export_data.xml",
        "views/llm_prompt_views.xml",
        "views/llm_prompt_tag_views.xml",
        "views/llm_prompt_category_views.xml",
        "views/llm_thread_views.xml",
        "views/menu.xml",
        "wizards/llm_prompt_test_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "llm_prompt/static/src/components/llm_chat_thread_header/llm_chat_thread_header.js",
            "llm_prompt/static/src/components/llm_chat_thread_header/llm_chat_thread_header.xml",
            "llm_prompt/static/src/models/llm_chat_thread_header_view.js",
            "llm_prompt/static/src/models/llm_prompt.js",
            "llm_prompt/static/src/models/thread.js",
            "llm_prompt/static/src/models/llm_chat.js",
        ],
    },
    "images": [
        "static/description/banner.jpeg",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
