{
    "name": "LLM ComfyICU Integration",
    "version": "17.0.1.0.0",
    "category": "Productivity/LLM",
    "summary": "Integration with ComfyICU API for media generation",
    "description": """
        This module integrates Odoo with ComfyICU API for media generation.
        It provides a new provider type that can be used with the LLM framework.
    """,
    "author": "Apexive Solutions LLC",
    "website": "https://github.com/apexive/odoo-llm",
    "license": "LGPL-3",
    "depends": [
        "llm",
        "llm_generate",
    ],
    "data": [
        "data/llm_publisher.xml",
    ],
    "images": [
        "static/description/banner.png",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
