18.0.1.0.4 (2026-01-09)
~~~~~~~~~~~~~~~~~~~~~~~

* [REQ] Now requires Letta server v0.16.0+ (for official Stainless SDK compatibility)
* [IMP] Now uses official letta-client SDK from PyPI (no longer requires forked version)
* [IMP] Install with: pip install letta-client
* [FIX] Fixed streaming not working - now properly streams tokens in real-time (stream_tokens=True)
* [KNOWN ISSUE] Three tools incompatible with Letta due to OpenAI strict mode requirements:
  - odoo_record_creator, odoo_record_updater, odoo_model_method_executor
  - These tools work with other LLM providers but not Letta
  - All other tools are fully compatible

18.0.1.0.3 (2026-01-08)
~~~~~~~~~~~~~~~~~~~~~~~

* [BREAKING] Complete SDK migration to Stainless-generated Letta Python SDK
* [FIX] Updated client initialization: token → api_key parameter
* [FIX] Updated imports: MessageCreate → MessageCreateParam
* [FIX] Updated imports: StreamableHttpServerConfig → CreateStreamableHTTPMcpServerParam
* [FIX] Updated message streaming: create_stream() → create(streaming=True)
* [FIX] Updated model listing: listembeddingmodels() → embeddings.list()
* [FIX] Updated MCP server API: client.tools.* → client.mcp_servers.*
* [FIX] Updated MCP tool listing to use server ID instead of server name
* [FIX] Updated agent methods: modify() → update() for updating agents
* [FIX] Updated agent methods: retrieve() uses positional agent_id
* [FIX] Updated tools.attach() and tools.detach() signatures (tool_id first, agent_id keyword-only)
* [FIX] Removed MCP server endpoint check (tools are in global registry)
* [FIX] Removed manual tool registration (tools auto-discovered from MCP servers)
* [IMP] Better error messages for MCP server and tool configuration issues
* [IMP] Now using MessageCreateParam for type safety when creating messages

18.0.1.0.2 (2026-01-08)
~~~~~~~~~~~~~~~~~~~~~~~

* [IMP] Updated for compatibility with new Letta SDK (Fern auto-generated)
* [FIX] Fixed agents.modify() to use agent_id as positional argument
* [IMP] SDK now supports 95% of methods unchanged, only modify() signature changed

18.0.1.0.1 (2025-12-01)
~~~~~~~~~~~~~~~~~~~~~~~

* [FIX] Added letta_normalize_prepend_messages() method to fix dispatch error

18.0.1.0.0
~~~~~~~~~~

* Initial release with Letta agent integration
