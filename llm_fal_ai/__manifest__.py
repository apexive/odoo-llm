{
    "name": "LLM - Fal.ai Provider",
    "summary": "Integration with the fal.ai API for LLM services",
    "description": """
        Integrates fal.ai services with the LLM module in Odoo.
        Allows the use of models and generation capabilities offered by fal.ai.
        Supports queue system for asynchronous processing.
    """,
    "author": "Apexive Solutions LLC",
    "website": "https://github.com/apexive/odoo-llm",
    "category": "Technical",
    "version": "16.0.1.1.3",
    "depends": ["llm", "llm_generate","llm_generate_job"],
    "external_dependencies": {
        "python": ["fal_client"]
    },
    "data": [
        "data/llm_publisher.xml",
        "data/llm_provider.xml",
        "data/llm_model.xml"
    ],
    "images": [
        "static/description/banner.jpeg"
    ],
    "license": "LGPL-3",
    "installable": True
}
