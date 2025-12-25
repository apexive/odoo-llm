{
    "name": "LLM A2A Integration",
    "version": "18.0.1.0.0",
    "category": "Technical",
    "summary": "Agent-to-Agent (A2A) protocol integration for LLM",
    "description": """
        Enables communication between AI agents using Google's A2A (Agent-to-Agent) protocol.

        Features:
        - Connect to external A2A agents
        - Delegate tasks to specialized agents
        - Agent discovery via Agent Cards
        - Streaming support for real-time responses
        - Multi-agent orchestration within LLM chat

        This module allows your Odoo LLM chat to communicate with any A2A-compatible
        agent running anywhere (local, cloud, different frameworks like LangChain, CrewAI, etc.)
    """,
    "author": "Apexive Solutions LLC",
    "website": "https://github.com/apexive/odoo-llm",
    "license": "LGPL-3",
    # Note: llm_knowledge is optional but if installed, A2A should load after it
    # for proper get_prepend_messages() MRO
    "depends": ["llm_thread", "llm_tool", "llm_assistant", "llm_knowledge"],
    "external_dependencies": {
        "python": ["httpx"],
    },
    "data": [
        "security/ir.model.access.csv",
        "security/llm_a2a_security.xml",
        "views/llm_a2a_agent_views.xml",
        "views/llm_menu_views.xml",
        "data/llm_tool_data.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "llm_a2a/static/src/**/*",
        ],
    },
    "auto_install": False,
    "application": False,
    "installable": True,
}
