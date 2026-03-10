{
    "name": "LLM Integration Base",
    "summary": """
        Integration with various LLM providers like Ollama, OpenAI, Replicate and Anthropic""",
    "description": """
        Provides integration with LLM (Large Language Model) providers for:
        - Chat completions
        - Text embeddings
        - Model management

    """,
    "author": "Apexive Solutions LLC",
    "website": "https://github.com/apexive/odoo-llm",
    "category": "Technical",
    "version": "18.0.1.7.2",
    "depends": ["mail", "web"],
    "data": [
        "security/llm_security.xml",
        "security/ir.model.access.csv",
        "wizards/fetch_models_views.xml",
        "views/llm_provider_views.xml",
        "views/llm_model_views.xml",
        "views/llm_publisher_views.xml",
        "views/llm_menu_views.xml",
        "data/mail_message_subtype.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "images": [
        "static/description/banner.jpeg",
    ],
}
