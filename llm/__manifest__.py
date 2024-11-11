{
    "name": "LLM Integration",
    "summary": """
        Integration with various LLM providers like Ollama, OpenAI, Replicate and Anthropic""",
    "description": """
        Provides integration with LLM (Large Language Model) providers for:
        - Chat completions
        - Text embeddings
        - Model management

        Supported providers:
        - OpenAI
        - Ollama
        - Replicate
        - Anthropic
    """,
    "author": "Apexive Solutions LLC",
    "website": "https://github.com/smartops-aero/flight",
    "category": "Technical",
    "version": "16.0.1.0.0",
    "depends": ["mail", "web"],
    "data": [
        "security/llm_security.xml",
        "security/ir.model.access.csv",
        "views/llm_views.xml",
        "views/llm_thread_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            # Base Models
            "llm/static/src/components/models.js",
            # Components
            "llm/static/src/components/llm_message/llm_message.js",
            "llm/static/src/components/llm_message/llm_message.scss",
            "llm/static/src/components/llm_message/llm_message.xml",
            "llm/static/src/components/llm_message_list/llm_message_list.js",
            "llm/static/src/components/llm_message_list/llm_message_list.scss",
            "llm/static/src/components/llm_message_list/llm_message_list.xml",
            "llm/static/src/components/llm_composer/llm_composer.js",
            "llm/static/src/components/llm_composer/llm_composer.scss",
            "llm/static/src/components/llm_composer/llm_composer.xml",
            "llm/static/src/components/llm_thread_view/llm_thread_view.js",
            "llm/static/src/components/llm_thread_view/llm_thread_view.scss",
            "llm/static/src/components/llm_thread_view/llm_thread_view.xml",
            "llm/static/src/components/llm_chat_dialog/llm_chat_dialog.js",
            "llm/static/src/components/llm_chat_dialog/llm_chat_dialog.xml",
        ],
    },
    "external_dependencies": {
        "python": ["openai", "replicate", "ollama", "anthropic"],
    },
    "installable": True,
}
