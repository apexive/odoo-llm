{
    "name": "LLM Generate Job",
    "version": "16.0.1.0.0",
    "category": "Artificial Intelligence",
    "summary": "Generation Job Management and Queue System for LLM Providers",
    "description": """
LLM Generate Job Management
===========================

This module provides a comprehensive generation job management system for LLM providers.

Features:
- Generation job creation and lifecycle management
- Provider-specific queue management
- Job status tracking and monitoring
- Retry and error handling mechanisms
- Direct vs. queued generation options
- PostgreSQL advisory locking integration

The system supports both direct generation (legacy mode) and queued generation
for better resource management and scalability.

Key Changes:
- Renamed from llm_generation_job to llm_generate_job
- Thread extension now only overrides generate_response() method
- Maintains backward compatibility with existing generate() method
""",
    "author": "Apexive",
    "website": "https://apexive.com",
    "depends": [
        "llm_thread",
        "llm_tool",
        "llm_generate"
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/llm_generation_cron.xml",
        "views/llm_generation_job_views.xml",
        "views/llm_generation_queue_views.xml",
        "views/llm_generation_menu_views.xml",
    ],
    "images": [
        "static/description/icon.svg",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
