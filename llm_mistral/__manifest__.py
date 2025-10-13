{
    "name": "Mistral AI LLM Integration",
    "summary": "Mistral AI provider integration for LLM module",
    "description": """
        Implements Mistral AI provider service for the LLM integration module.
        Supports Mistral models for chat and embedding capabilities.
    """,
    "author": "Apexive Solutions LLC",
    "website": "https://github.com/apexive/odoo-llm",
    "category": "Technical",
    "version": "17.0.1.0.0",
    "depends": ["base", "llm_openai"],
    "external_dependencies": {
        "python": ["mistralai"],
    },
    "data": [
        "data/llm_publisher.xml",
        "data/llm_provider.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
}
