{
    "name": "LLM ComfyUI Integration",
    "version": "17.0.1.0.2",
    "category": "Productivity/LLM",
    "summary": "Integration with ComfyUI API for media generation",
    "description": """
        This module integrates Odoo with ComfyUI API for media generation.
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
        "data/llm_prompt_category_data.xml",
        "data/llm_prompt_data.xml",
    ],
    "images": [
        "static/description/banner.png",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
