{
    "name": "LLM Media Generation",
    "version": "16.0.1.0.2",
    "category": "Productivity/Discuss",
    "summary": "Media generation capabilities for LLM models",
    "description": """
        Adds support for generating images, audio, and other media using LLM models.
        
        Features:
        - Dynamic form generation based on model input schemas
        - JSON editor for advanced configuration
        - Prompt template integration with assistant defaults
        - Streaming media generation responses
        - Support for various media types (images, audio, etc.)
    """,
    "author": "Apexive Solutions LLC",
    "website": "https://github.com/apexive/odoo-llm",
    "depends": [
        "llm",
        "llm_thread",
        "llm_mail_message_subtypes",
        "web_json_editor",
        "llm_prompt",
        "llm_assistant",
    ],
    "data": [
        "data/llm_tool_data.xml",
        "views/llm_model_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            # JavaScript Models
            "llm_generate/static/src/models/llm_model.js",
            "llm_generate/static/src/models/llm_chat.js",
            "llm_generate/static/src/models/composer.js",
            "llm_generate/static/src/models/message.js",

            # Components
            "llm_generate/static/src/components/llm_media_form/llm_form_fields_view.js",
            "llm_generate/static/src/components/llm_media_form/llm_media_form.js",
            "llm_generate/static/src/components/llm_chat_composer/llm_chat_composer.js",

            # Templates
            "llm_generate/static/src/components/llm_media_form/llm_form_fields_view.xml",
            "llm_generate/static/src/components/llm_media_form/llm_media_form.xml",
            "llm_generate/static/src/components/llm_chat_composer/llm_chat_composer.xml",
            "llm_generate/static/src/components/message/message.xml",

            # Styles
            "llm_generate/static/src/components/llm_media_form/llm_media_form.scss",
            "llm_generate/static/src/components/message/message.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
