{
    "name": "Anthropic LLM Integration",
    "summary": "Anthropic Claude provider integration for LLM module",
    "description": """
        Implements Anthropic provider service for the LLM integration module.
        Supports Claude models for chat, multimodal, and tool calling capabilities.

        Features:
        - Claude 4.5, 4, and 3.x model support
        - Tool/function calling
        - Extended thinking support
        - Streaming responses
        - Multimodal (vision) capabilities
    """,
    "author": "Apexive Solutions LLC",
    "contributors": [
        "Crottolo <bo@fl1.cz>",
    ],
    "website": "https://github.com/apexive/odoo-llm",
    "category": "Technical",
    "version": "17.0.1.1.0",
    "depends": ["llm", "llm_tool"],
    "external_dependencies": {
        "python": ["anthropic"],
    },
    "data": [
        "data/llm_publisher.xml",
    ],
    "images": [
        "static/description/banner.jpeg",
    ],
    "license": "LGPL-3",
    "installable": True,
}
