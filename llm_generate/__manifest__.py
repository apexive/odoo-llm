{
    "name": "LLM Content Generation",
    "version": "17.0.2.0.0",
    "category": "Productivity/Discuss",
    "summary": "Content generation capabilities for LLM models",
    "description": """
        Clean content generation using LLM models with the new generate() API.

        Features:
        - Uses body_json for structured generation data
        - Simple prompt rendering with context merging
        - Direct integration with main LLM module's generate() method
        - Minimal, clean code with focused functionality
        - Works with details field for schema storage
    """,
    "author": "Apexive Solutions LLC",
    "website": "https://github.com/apexive/odoo-llm",
    "depends": [
        "llm",
        "llm_thread",
        "llm_assistant",
        "web_json_editor",
    ],
    "data": [
        "data/llm_tool_data.xml",
        "views/llm_model_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            # Patches - Extend existing services and components
            "llm_generate/static/src/patches/llm_store_service_patch.js",
            "llm_generate/static/src/patches/composer_patch.js",
            "llm_generate/static/src/patches/message_patch.js",
            "llm_generate/static/src/patches/llm_chat_container_patch.js",
            # Components
            "llm_generate/static/src/components/llm_media_form/llm_form_fields_view.js",
            "llm_generate/static/src/components/llm_media_form/llm_media_form.js",
            # Templates
            "llm_generate/static/src/components/llm_media_form/llm_form_fields_view.xml",
            "llm_generate/static/src/components/llm_media_form/llm_media_form.xml",
            "llm_generate/static/src/templates/llm_chat_container_extension.xml",
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
