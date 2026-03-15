{
    "name": "LLM RAG Mistral",
    "summary": "OCR vision AI: extract text from images, receipts, handwriting, and scanned documents using Mistral vision models",
    "description": """
        Turn images into searchable knowledge with Mistral AI's vision models. Extract text from
        handwritten notes, receipts, scanned documents, screenshots, and product labels. Make every
        image searchable in your knowledge base with automatic OCR processing.
    """,
    "category": "Technical",
    "version": "17.0.1.0.0",
    "depends": ["llm_knowledge", "llm_mistral", "llm_tool"],
    "author": "Apexive Solutions LLC",
    "website": "https://github.com/apexive/odoo-llm",
    "data": [
        "data/llm_tool_data.xml",
        "views/llm_resource_views.xml",
    ],
    "images": ["static/description/banner.jpeg"],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
