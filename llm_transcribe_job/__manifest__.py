{
    "name": "LLM Transcribe Job",
    "version": "18.0.1.0.0",
    "category": "Artificial Intelligence",
    "summary": "Transcription Job Management and Queue System for LLM Providers",
    "description": """
LLM Transcribe Job Management
=============================

This module provides a comprehensive transcription job management system for LLM providers.

Features:
- Transcription job creation and lifecycle management
- Provider-specific queue management
- Job status tracking and monitoring
- Retry and error handling mechanisms
- Direct vs. queued transcription options
- PostgreSQL advisory locking integration

The system supports both direct transcription (legacy mode) and queued transcription
for better resource management and scalability.

Key Changes:
- Adds queue-aware thread execution for transcription models
- Mirrors the llm_generate_job architecture for async transcription
- Maintains backward compatibility with direct transcription execution
""",
    "author": "Apexive",
    "website": "https://github.com/apexive/odoo-llm",
    "depends": [
        "llm_thread",
        "llm_tool",
        "llm_transcribe",
        "web_json_editor",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/llm_transcription_cron.xml",
        "views/llm_transcription_job_views.xml",
        "views/llm_transcription_queue_views.xml",
        "views/llm_transcription_menu_views.xml",
    ],
    "images": [
        "static/description/icon.svg",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
