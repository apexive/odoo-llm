LLM MCP Server for Odoo
========================

HTTP-based MCP server that exposes Odoo tools to any MCP-compatible AI client.

**Module Type:** 📦 Infrastructure (External AI Integration)

Ecosystem Architecture
======================

::

    ┌───────────────────────────────────────────────────────────────┐
    │                    External AI Clients                        │
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │
    │  │Claude Desktop│  │ Claude Code │  │  Cursor / Codex     │   │
    │  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘   │
    └─────────┼────────────────┼────────────────────┼──────────────┘
              └────────────────┼────────────────────┘
                               │ MCP Protocol
                               ▼
                  ┌───────────────────────────────────────────┐
                  │     ★ llm_mcp_server (This Module) ★      │
                  │         MCP Server for Odoo               │
                  │  🔌 HTTP API │ 🔐 Auth │ 🛠️ Tool Bridge   │
                  └─────────────────────┬─────────────────────┘
                                        │
                            ┌───────────┴───────────┐
                            ▼                       ▼
        ┌───────────────────────────┐   ┌───────────────────────────┐
        │         llm_tool          │   │           llm             │
        │    (Tool Registry)        │   │    (Core Base Module)     │
        └───────────────────────────┘   └───────────────────────────┘

Installation
============

What to Install
---------------

**For external AI tool access:**

.. code-block:: bash

    odoo-bin -d your_db -i llm_mcp_server

Auto-Installed Dependencies
---------------------------

- ``llm`` (core infrastructure)
- ``llm_tool`` (tool framework)

Why Use This Module?
--------------------

+-----------------+---------------------------------+
| Feature         | llm_mcp_server                  |
+=================+=================================+
| **External AI** | 🤖 Claude Desktop, Cursor, etc. |
+-----------------+---------------------------------+
| **Secure**      | 🔐 API key authentication       |
+-----------------+---------------------------------+
| **Standard**    | 📡 MCP protocol (Anthropic)     |
+-----------------+---------------------------------+
| **All Tools**   | 🛠️ Exposes all Odoo LLM tools   |
+-----------------+---------------------------------+

Common Setups
-------------

+-----------------------+----------------------------------------------------------+
| I want to...          | Install                                                  |
+=======================+==========================================================+
| Claude Desktop + Odoo | ``llm_mcp_server``                                       |
+-----------------------+----------------------------------------------------------+
| External + knowledge  | ``llm_mcp_server`` + ``llm_tool_knowledge`` +            |
|                       | ``llm_pgvector``                                         |
+-----------------------+----------------------------------------------------------+
| External + Letta      | ``llm_mcp_server`` + ``llm_letta``                       |
+-----------------------+----------------------------------------------------------+

What is MCP?
------------

`Model Context Protocol (MCP) <https://modelcontextprotocol.io/>`_ is an open standard by Anthropic that lets AI assistants securely access external tools and data sources. This module implements an MCP server directly in Odoo.

Requirements
------------

- **Python**: 3.10+
- **Odoo**: 18.0
- **Dependencies**: See `requirements.txt <https://github.com/apexive/odoo-llm/blob/18.0/requirements.txt>`_

Quick Start
-----------

1. Install Module
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   odoo-bin -d your_db -i llm_mcp_server

2. Get API Key
~~~~~~~~~~~~~~

**Option A (Recommended):** Use the "New MCP Key" button:

- User Preferences → Account Security → **New MCP Key**, or
- LLM → Configuration → MCP Server → **New MCP Key**

This generates an API key with ready-to-copy client configurations.

**Option B:** Create a standard API key:

- User Preferences → Account Security → API Keys → New

3. Configure Client
~~~~~~~~~~~~~~~~~~~

**Claude Desktop** (``~/.config/claude_desktop/claude_desktop_config.json``):

.. code-block:: json

   {
     "mcpServers": {
       "odoo-llm-mcp-server": {
         "type": "stdio",
         "command": "npx",
         "args": ["-y", "mcp-remote", "http://localhost:8069/mcp",
                  "--header", "Authorization: Bearer YOUR_API_KEY"],
         "env": { "MCP_TRANSPORT": "streamable-http" }
       }
     }
   }

**Claude Code**:

.. code-block:: bash

   claude mcp add-json odoo-llm-mcp-server '{
     "type": "stdio",
     "command": "npx",
     "args": ["-y", "mcp-remote", "http://localhost:8069/mcp",
              "--header", "Authorization: Bearer YOUR_API_KEY"],
     "env": {"MCP_TRANSPORT": "streamable-http"}
   }'

**Codex CLI** (``~/.codex/config.toml``):

.. code-block:: toml

   experimental_use_rmcp_client = true

   [mcp_servers.odoo-llm-mcp-server]
   url = "http://localhost:8069/mcp"
   http_headers.Authorization = "Bearer YOUR_API_KEY"

**Other clients**: Connect to ``http://localhost:8069/mcp`` with Bearer auth

4. Restart & Test
~~~~~~~~~~~~~~~~~

Restart your client → Ask "What tools do you have?"

Architecture
------------

::

   ┌─────────────┐   streamable-http   ┌──────────────┐      ┌─────────────┐
   │ MCP Client  │ ←─────────────────→ │ Odoo MCP     │ ───→ │ llm.tool    │
   │ (Claude)    │   JSON-RPC 2.0      │ Controller   │      │ Registry    │
   └─────────────┘                     └──────────────┘      └─────────────┘

- **Protocol**: MCP 2025-06-18 spec via JSON-RPC 2.0
- **Transport**: ``streamable-http`` (HTTP with streaming responses)
- **Endpoint**: ``/mcp`` (POST for requests, streaming responses)
- **Auth**: Bearer token (Odoo API keys)
- **Tools**: Auto-discovered from ``llm.tool`` registry

Request Flow
~~~~~~~~~~~~

1. Client sends JSON-RPC request to ``/mcp`` via POST
2. Server validates Bearer token → loads user session
3. For ``tools/list``: Returns all active tools user can access
4. For ``tools/call``: Executes tool with user's permissions
5. Response streamed back via HTTP streaming

API Reference
-------------

Initialize
~~~~~~~~~~

.. code-block:: json

   // Request
   {"jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {"protocolVersion": "2025-06-18", "capabilities": {}}}

   // Response
   {"jsonrpc": "2.0", "id": 1,
    "result": {"protocolVersion": "2025-06-18",
               "capabilities": {"tools": {}},
               "serverInfo": {"name": "odoo-mcp-server", "version": "1.0.0"}}}

List Tools
~~~~~~~~~~

.. code-block:: json

   // Request
   {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}

   // Response
   {"jsonrpc": "2.0", "id": 2,
    "result": {"tools": [
      {"name": "search_records",
       "description": "Search for records in any Odoo model",
       "inputSchema": {"type": "object", "properties": {...}}}
    ]}}

Call Tool
~~~~~~~~~

.. code-block:: json

   // Request
   {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
    "params": {"name": "search_records",
               "arguments": {"model": "res.partner", "domain": []}}}

   // Response
   {"jsonrpc": "2.0", "id": 3,
    "result": {"content": [{"type": "text", "text": "..."}]}}

Creating Tools
--------------

Tools are auto-discovered from the ``llm.tool`` model. See `llm_tool module <https://github.com/apexive/odoo-llm/tree/18.0/llm_tool>`_ for creating custom tools.

Testing & Debugging
-------------------

**MCP Inspector**: https://modelcontextprotocol.io/docs/tools/inspector

Test your server:

- Verify connectivity
- Browse available tools
- Test tool execution
- Debug authentication issues

**Odoo Logs**: Check server logs for MCP-related errors

.. code-block:: bash

   # Enable debug mode
   odoo-bin --log-level=debug

Troubleshooting
---------------

**No tools showing up?**

- Check that tools are active in Odoo (LLM → Tools)
- Verify API key has access to tools
- Check user permissions

**Authentication failed?**

- Verify API key is correct
- Check key hasn't expired
- Ensure Bearer token format: ``Authorization: Bearer YOUR_KEY``

**Connection refused?**

- Verify Odoo is running on specified port
- Check firewall settings
- For remote access, ensure Odoo is accessible from client

**Tools failing to execute?**

- Check Odoo logs for errors
- Verify user has required permissions
- Test tool manually in Odoo UI first

Security
--------

- **User-scoped**: Each API key executes with that user's permissions
- **ACL enforced**: All Odoo access control rules apply
- **No shared state**: Each request is isolated
- **Audit trail**: All tool calls logged in Odoo

Roadmap
-------

Future enhancements planned:

- **MCP Resources** - Expose Odoo records and documents as MCP resources for context injection
- **MCP Prompts** - Pre-built prompts for common Odoo workflows (sales, inventory, accounting)
- **MCP Utilities** - Additional MCP features like sampling and logging support

Contributions and feature requests welcome!

Resources
---------

- `MCP Protocol Spec <https://modelcontextprotocol.io/>`_
- `Odoo LLM Repository <https://github.com/apexive/odoo-llm>`_
- `Video Tutorial <https://drive.google.com/file/d/1TgPrfLuAtql3en3B_McKlMmDWuYn3wXM/view>`_
