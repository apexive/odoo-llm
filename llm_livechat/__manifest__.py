{
    "name": "LLM Live Chat Integration",
    "version": "18.0.1.0.0",
    "category": "Productivity/AI",
    "summary": "Connect LLM Assistants to Live Chat for automatic visitor responses",
    "description": """
LLM Live Chat Integration
==========================

This module integrates LLM Assistants with Odoo's Live Chat system to provide
automated AI-powered responses to website visitors.

Features:
- Configure AI assistants per live chat channel
- Automatic response to visitor messages
- Configurable delay before auto-reply
- Thread-based conversation management
- Full conversation history
    """,
    "author": "Apexive Solutions LLC",
    "website": "https://github.com/apexive/odoo-llm",
    "depends": [
        "llm_assistant",
        "im_livechat",
    ],
    "data": [
        "views/im_livechat_channel_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
    "license": "LGPL-3",
}
