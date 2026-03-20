# LLM MCP Client

Connect Odoo AI assistants to **external MCP servers** as tool sources.

While `llm_mcp_server` makes Odoo *expose* tools to external AI clients,
this module does the reverse: it lets Odoo *consume* tools from any remote
[Model Context Protocol](https://modelcontextprotocol.io) server.

---

## How it works

```
llm.thread (AI assistant chat)
    ↓  tool call from LLM
llm.tool  (implementation = 'mcp_client')
    ↓  HTTP JSON-RPC  tools/call
Remote MCP Server  (GitHub, Brave Search, your own service, …)
    ↓  result text
Back to the assistant conversation
```

1. **Configure** an MCP Server record with URL + optional Bearer token.
2. **Sync Tools** — calls `tools/list` on the remote server and upserts
   `llm.tool` records with `implementation = 'mcp_client'`.
3. **Assign** those tools to any `llm.assistant` or `llm.thread` as normal.
4. When the LLM decides to call the tool, this module proxies the
   `tools/call` request and returns the result to the conversation.

---

## Configuration

### LLM → Configuration → MCP Servers (Client)

| Field | Description |
|-------|-------------|
| Name | Label shown in the tool form |
| MCP Endpoint URL | Full URL, e.g. `https://mcp.example.com/mcp` |
| Auth Type | `No Authentication` or `Bearer Token` |
| Bearer Token | Sent as `Authorization: Bearer <token>` |
| Timeout | HTTP timeout in seconds (default 30) |

### Sync Tools

Click **Sync Tools** on the server form to:
- Fetch `tools/list` from the remote server
- Create `llm.tool` records for new tools
- Update changed tools (name, description, schema)
- Deactivate tools no longer advertised by the server

### Test Connection

Click **Test Connection** to verify reachability (sends `initialize` + `ping`).

---

## Supported MCP servers

Any server implementing the MCP 2025-06-18 JSON-RPC protocol over HTTP,
including:

- [MCP filesystem server](https://github.com/modelcontextprotocol/servers)
- [Brave Search MCP](https://github.com/modelcontextprotocol/servers/tree/main/src/brave-search)
- [GitHub MCP](https://github.com/github/github-mcp-server)
- [Odoo's own `llm_mcp_server`](../llm_mcp_server) (connect two Odoo instances!)
- Any custom MCP server you build with the MCP SDK

---

## Technical notes

- The `mcp_client` implementation type is registered via the existing
  `_get_available_implementations()` hook in `llm.tool` — no core changes.
- `mcp_client_execute(**kwargs)` is automatically picked up by
  `_get_implementation_method()` via the `{implementation}_execute` pattern.
- `get_input_schema()` returns the schema stored during sync, bypassing
  the MCP SDK introspection path used for `@llm_tool` decorated methods.
- Mixed threads work fine: a single `llm.thread` can have both local
  `function` tools and remote `mcp_client` tools simultaneously.

---

## Dependencies

- `llm_tool` (part of odoo-llm)
- Python `requests` library (standard in Odoo environments)
