{
    "name": "LLM Transcribe",
    "summary": "Provider-agnostic transcription tools for LLM assistants",
    "description": """
        Adds transcription tools for LLM assistants.
        The module exposes a model-driven audio transcription tool
        that mirrors odoo_generate but targets speech-to-text workflows.
    """,
    "category": "Technical/AI",
    "version": "18.0.2.0.0",
    "depends": [
        "llm",
        "llm_thread",
        "llm_tool",
        "llm_assistant",
        "web_json_editor",
    ],
    "author": "Apexive Solutions LLC",
    "website": "https://github.com/apexive/odoo-llm",
    "data": [
        "data/llm_tool_data.xml",
        "views/llm_model_views.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
