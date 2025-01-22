{
    "name": "LLM Thread",
    "summary": "Message thread support for LLM conversations",
    "description": """
        Extends the LLM integration module with conversation threading capabilities:
        - Persistent chat history
        - Real-time streaming responses
        - Message management
        - Thread organization
        - Chat export
    """,
    "category": "Technical",
    "version": "16.0.1.0.0",
    "depends": ["llm", "mail"],
    "external_dependencies": {"python": ["markdown2"]},
    "data": [
        "data/mail_message_subtype.xml",
        "security/llm_thread_security.xml",
        "security/ir.model.access.csv",
        "views/llm_model_views.xml",
        "views/llm_thread_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            ("include", "web_editor.assets_wysiwyg"),
            "llm_thread/static/src/components/icons.xml",
            "llm_thread/static/src/components/icons.scss",
            "llm_thread/static/src/components/composer_view/composer_view.xml",
            "llm_thread/static/src/components/composer_view/composer_view.scss",
            "llm_thread/static/src/components/composer_view/composer_view_patch.js",
        ],
    },
    "license": "LGPL-3",
    "installable": True,
}
