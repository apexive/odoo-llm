{
    "name": "LLM Training Management",
    "summary": """
        Manage LLM fine-tuning datasets and training jobs""",
    "description": """
        Provides management of training datasets and fine-tuning jobs for LLMs:
        - Dataset management for fine-tuning
        - Training job configuration and tracking
        - Integration with LLM providers for fine-tuning
    """,
    "author": "Apexive Solutions LLC",
    "website": "https://github.com/apexive/odoo-llm",
    "category": "Technical",
    "version": "16.0.1.0.0",
    "depends": ["base", "mail", "llm", "llm_thread", "llm_assistant", "llm_prompt", "llm_fal_ai"],
    "data": [
        "security/llm_training_security.xml",
        "security/ir.model.access.csv",
        "views/llm_training_dataset_views.xml",
        "views/llm_training_job_views.xml",
        "views/llm_training_job_avatar_views.xml",
        "views/llm_training_menu_views.xml",
        "views/llm_thread_training_views.xml",
    ],
    "images": [
        "static/description/banner.jpeg",
    ],
    "license": "LGPL-3",
    "installable": True,
    "auto_install": False,
}
