{
    "name": "Mistral OCR Tool",
    "summary": "Extract text from images and PDFs using Mistral AI vision models",
    "description": """
        Standalone OCR tool using Mistral's vision models to extract text from:
        - Invoice PDFs and images
        - Receipts and bills
        - Scanned documents
        - Handwritten notes
        - Product labels and packaging
        - Screenshots and photos

        This tool can be used by any LLM assistant for document parsing.
        Minimal dependencies - no knowledge base required.
    """,
    "category": "Technical/AI",
    "version": "17.0.1.0.1",
    "depends": [
        "llm_mistral",  # Mistral AI provider
        "llm_tool",  # Tool registration framework
    ],
    "author": "Apexive Solutions LLC",
    "website": "https://github.com/apexive/odoo-llm",
    "data": [
        "data/llm_tool_data.xml",
    ],
    "images": [
        "static/description/banner.jpeg",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}
