{
    "name": "LLM Knowledge Integration for Document Pages",
    "summary": "Integrate document.page with LLM RAG for knowledge base search",
    "description": """
        Integrates the Document Page module with LLM RAG.

        Features:
        - Parse document pages into LLM Knowledge resources
        - Include document hierarchy in generated content
        - Maintain metadata like contributors and update dates
        - Create RAG resources from document pages
    """,
    "category": "Knowledge",
    "version": "17.0.1.0.0",
    "depends": ["document_page", "llm_knowledge"],
    "external_dependencies": {
        "python": ["markdownify"],
    },
    "author": "Apexive Solutions LLC",
    "website": "https://github.com/apexive/odoo-llm",
    "license": "AGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
    "images": [
        "static/description/banner.jpeg",
    ],
    "data": [
        "views/document_page_views.xml",
        "wizards/upload_resource_wizard_views.xml",
    ],
}
