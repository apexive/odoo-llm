{
    "name": "Replicate LLM Integration",
    "summary": "Replicate provider integration for LLM module",
    "description": """
        Implements Replicate provider service for the LLM integration module.
        Supports diverse AI models and custom model deployments.
    """,
    "category": "Technical",
    "version": "17.0.1.1.1",
    "depends": ["llm", "llm_generate"],
    "external_dependencies": {
        "python": ["replicate", "jsonref"],
    },
    "data": [
        "data/llm_publisher.xml",
        "views/replicate_model_views.xml",
    ],
    "images": [
        "static/description/banner.jpeg",
    ],
    "website": "https://github.com/apexive/odoo-llm",
    "author": "Apexive Solutions LLC",
    "license": "LGPL-3",
    "installable": True,
}
