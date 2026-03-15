{
    "name": "LLM Tool RAG",
    "version": "17.0.1.0.1",
    "category": "Productivity/Tools",
    "author": "Apexive Solutions LLC",
    "website": "https://github.com/apexive/odoo-llm",
    "summary": "RAG tools for AI assistants: semantic search, knowledge retrieval, source citations, and function calling for LLM chat integration",
    "description": """
        Give your AI assistants instant access to your knowledge base. This module provides
        RAG tools that enable LLM assistants to search documents, cite sources, and answer
        questions using your actual company data instead of just their training.
    """,
    "depends": ["llm_knowledge", "llm_tool", "llm_assistant"],
    "data": [
        "data/llm_tool_data.xml",
        "data/llm_assistant_data.xml",
    ],
    "images": [
        "static/description/banner.jpeg",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
    "maintainer": "Apexive Solutions LLC",
}
