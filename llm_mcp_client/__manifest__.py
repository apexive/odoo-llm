{
    "name": "LLM MCP Client",
    "version": "18.0.1.0.0",
    "category": "Technical",
    "summary": "Connect Odoo AI assistants to external MCP servers as tool sources",
    "description": """
        LLM MCP Client

        Allows Odoo AI assistants (llm.thread / llm.assistant) to consume tools
        from any remote MCP (Model Context Protocol) server — GitHub Copilot,
        Brave Search, filesystem servers, custom internal services, etc.

        How it works
        ─────────────
        1. Configure an **MCP Server** record with URL + optional Bearer token.
        2. Click **Sync Tools** — the module calls the server's ``tools/list``
           endpoint and creates ``llm.tool`` records with
           ``implementation = 'mcp_client'``.
        3. Add those tool records to any ``llm.assistant`` or ``llm.thread``
           the same way you add any other tool.
        4. When the assistant calls the tool, this module proxies the
           ``tools/call`` request to the remote server and returns the result.

        Features
        ─────────
        • Supports Bearer token and no-auth remote MCP servers
        • Full ``tools/list`` → ``llm.tool`` sync with schema preservation
        • Idempotent re-sync: updates changed tools, deactivates removed ones
        • Per-server sync status and last-sync timestamp
        • Timeout and error handling per tool call
        • Works alongside local ``@llm_tool`` decorated tools — mixed threads OK
    """,
    "author": "Apexive Solutions LLC",
    "website": "https://github.com/apexive/odoo-llm",
    "license": "LGPL-3",
    "depends": ["llm_tool"],
    "external_dependencies": {
        "python": ["requests"],
    },
    "data": [
        "security/ir.model.access.csv",
        "data/llm_mcp_client_default_servers.xml",
        "views/llm_mcp_client_server_views.xml",
        "views/llm_tool_views.xml",
        "views/menu.xml",
    ],
    "auto_install": False,
    "application": False,
    "installable": True,
}
