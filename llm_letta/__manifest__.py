{
    "name": "Letta LLM Integration",
    "summary": "Letta agent-based AI with persistent memory and MCP tools",
    "description": """
        Integrates Letta platform for stateful AI agents with persistent memory.

        Features:
        • Agent-based conversations with memory persistence
        • Full MCP (Model Context Protocol) tool integration
        • Automatic agent lifecycle management with threads
        • Support for both Letta Cloud and self-hosted servers
        • Real-time streaming responses

        Requires Letta server v0.16.0+ and llm_mcp_server module.
    """,
    "author": "Apexive Solutions LLC",
    "website": "https://github.com/apexive/odoo-llm",
    "category": "Technical",
    "version": "17.0.1.0.4",
    "depends": ["llm", "llm_thread", "llm_assistant", "llm_mcp_server"],
    "external_dependencies": {
        "python": ["letta-client"],
    },
    "data": [
        "security/res_groups.xml",
        "data/llm_publisher.xml",
        "data/llm_provider.xml",
        "views/llm_thread_views.xml",
    ],
    "images": [
        "static/description/banner.jpeg",
    ],
    "license": "LGPL-3",
    "installable": True,
}
