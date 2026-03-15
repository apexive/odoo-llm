{
    "name": "LLM Knowledge Automation",
    "summary": "Auto-sync knowledge base: keeps AI current with real-time data updates, domain filters, and automated RAG pipeline processing",
    "description": """
        Set it and forget it - your AI's knowledge stays automatically updated as your data changes.
        No manual sync required. Domain filters automatically create, update, and remove documents
        from knowledge collections when records change. RAG pipeline runs automatically.
    """,
    "category": "Technical",
    "version": "17.0.1.0.0",
    "depends": ["llm_knowledge", "base_automation"],
    "external_dependencies": {
        "python": [],
    },
    "author": "Apexive Solutions LLC",
    "website": "https://github.com/apexive/odoo-llm",
    "data": [
        "views/llm_knowledge_collection_views.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
    "images": [
        "static/description/banner.jpeg",
    ],
}
