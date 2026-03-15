{
    "name": "LLM - Fal.ai Provider",
    "summary": "Integration with the fal.ai API for LLM generation services",
    "description": """
        Integrates fal.ai services with the LLM module in Odoo.
        Provides unified generate() endpoint for image generation using fal.ai models.
        Uses model details field for schema storage and supports both sync and async generation.
    """,
    "author": "Apexive Solutions LLC",
    "website": "https://github.com/apexive/odoo-llm",
    "category": "Technical",
    "version": "17.0.2.0.1",
    "depends": ["llm", "llm_generate_job"],
    "external_dependencies": {"python": ["fal_client"]},
    "data": ["data/llm_publisher.xml"],
    "images": ["static/description/banner.jpeg"],
    "license": "LGPL-3",
    "installable": True,
}
