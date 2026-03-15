{
    "name": "LLM MCP Server",
    "version": "17.0.1.3.2",
    "category": "Technical",
    "summary": "MCP server exposing Odoo LLM tools to Claude Desktop and other MCP hosts",
    "description": """
        Model Context Protocol (MCP) Server for Odoo LLM

        Enables Claude Desktop, Letta, and other MCP hosts to access and execute
        Odoo tools directly through a standards-compliant MCP server.

        Core Features:
        • MCP 2025-06-18 protocol compliance with JSON-RPC 2.0
        • Bearer token authentication with Odoo user integration
        • Stateful session management with concurrent request handling
        • Automatic tool discovery from llm.tool registry
        • Real-time tool execution with proper Odoo context
        • Health monitoring and protocol version negotiation
        • Production-ready with optimized logging and error handling

        Supported Methods:
        • initialize - Server capability negotiation
        • tools/list - Dynamic tool discovery
        • tools/call - Authenticated tool execution
        • ping - Connection health checks
    """,
    "author": "Apexive Solutions LLC",
    "website": "https://github.com/apexive/odoo-llm",
    "license": "LGPL-3",
    "depends": ["base", "llm", "llm_tool", "web_json_editor"],
    "external_dependencies": {
        "python": ["mcp"],
    },
    "data": [
        "security/ir.model.access.csv",
        "data/llm_mcp_server_config.xml",
        "views/llm_mcp_server_config_views.xml",
        "views/llm_mcp_session_views.xml",
        "views/res_users_views.xml",
        "wizards/mcp_key_wizard_views.xml",
    ],
    "images": [
        "static/description/banner.jpeg",
        "static/description/llm_mcp_server_demo.gif",
        "static/description/client_claude_desktop.png",
        "static/description/client_claude_code.png",
        "static/description/client_cursor.png",
        "static/description/client_windsurf.png",
        "static/description/client_vscode.png",
        "static/description/client_codex.png",
        "static/description/client_claude_cowork.png",
    ],
    "auto_install": False,
    "application": False,
    "installable": True,
}
