{
    "name": "LLM Generate Job",
    "summary": """
        Manage long-running generation jobs with webhook support""",
    "description": """
        Provides management of long-running generation jobs for LLMs:
        - Generation job queue management with states
        - Webhook URL support for asynchronous generation completion
        - Integration with threads for result delivery
        - Support for image, video and other media generation queues
        - Job visibility control in tree views
    """,
    "author": "Apexive Solutions LLC",
    "website": "https://github.com/apexive/odoo-llm",
    "category": "Technical",
    "version": "16.0.1.0.0",
    "depends": [
        "base", 
        "mail", 
        "llm", 
        "llm_thread", 
        "llm_generate",
        "llm_mail_message_subtypes"
    ],    
    "data": [
        "security/llm_generate_job_security.xml",
        "security/ir.model.access.csv",
        "views/llm_generate_job_views.xml",
        "views/llm_generate_job_menu_views.xml",
        "data/llm_generate_job_data.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "llm_generate_job/static/src/js/notification_service.js",
            "llm_generate_job/static/src/js/thread_patch.js",
        ],
    },
    "license": "LGPL-3",
    "installable": True,
    "auto_install": False,
}
