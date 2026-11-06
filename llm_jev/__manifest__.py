# Copyright 2026 Lijo Antony
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html).

{
    "name": "TypeSafe Jev LLM Integration",
    "summary": "TypeSafe Jev typed decision provider integration for LLM module",
    "version": "18.0.1.0.0",
    "category": "Technical",
    "author": "Lijo Antony",
    "website": "https://github.com/apexive/odoo-llm",
    "license": "LGPL-3",
    "depends": ["llm"],
    "external_dependencies": {
        "python": ["requests"],
    },
    "data": [
        "data/llm_publisher.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
