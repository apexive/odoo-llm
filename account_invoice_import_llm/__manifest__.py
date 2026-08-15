{
    "name": "Account Invoice Import LLM",
    "summary": "AI-powered invoice data extraction with OCR for OCA account_invoice_import",
    "description": """
        Integrates LLM-OCR extraction into OCA's account_invoice_import wizard.
        Extracts invoice data from PDFs and images when embedded XML is not available.
    """,
    "category": "Accounting/AI",
    "version": "18.0.1.2.0",
    "depends": [
        "account_invoice_import",  # OCA invoice import wizard
        "llm_assistant",  # LLM infrastructure
        "llm_mistral",  # Mistral provider (for OCR)
    ],
    "author": "Apexive Solutions LLC",
    "website": "https://github.com/apexive/odoo-llm",
    "data": [
        "data/llm_prompt_invoice_data.xml",
        "data/llm_assistant_data.xml",
        "views/account_move_views.xml",
    ],
    "images": [
        "static/description/banner.jpeg",
    ],
    "license": "AGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
    "pre_init_hook": "pre_init_hook",
}
