# LLM MCP Server for Odoo

Production-ready Model Context Protocol (MCP) server that exposes Odoo LLM tools to AI clients.

**✅ Verified Working With:**

- **Claude Desktop** - Full integration with native MCP support
- **Letta Agents** - Complete tool discovery and execution
- **Any MCP-compatible client** - Standards-compliant implementation

## Quick Start

1. **Configure MCP Server**: Go to **LLM → Configuration → MCP Server** and copy your API key
2. **Add to Claude Desktop**: Use the configuration below with your API key
3. **Start using**: Ask Claude "What tools do you have available?"

## Core Features

- **Native Odoo Implementation**: 100% pure Odoo module using standard HTTP controllers and models
- **MCP 2025-06-18 Compliance**: Full protocol implementation with JSON-RPC 2.0
- **Bearer Authentication**: Secure API key-based authentication
- **Auto Tool Discovery**: Exposes all active `llm.tool` records automatically
- **Session Management**: Stateful operation with concurrent request handling
- **Production Ready**: Optimized logging, error handling, and performance
- **Future SSE Support**: Architecture ready for Server-Sent Events streaming (planned)

## Integration with Claude Desktop

### Prerequisites

1. **Install mcp-remote globally**:

   ```bash
   npm install -g mcp-remote
   ```

2. **Get your API key** from Odoo:
   - Follow -> https://www.odoo.com/documentation/17.0/developer/reference/external_api.html#api-keys

### Claude Desktop Configuration

Add this configuration to your Claude Desktop config file:

**Location**: `~/.config/claude_desktop/claude_desktop_config.json` (Linux/macOS) or `%APPDATA%/Claude/claude_desktop_config.json` (Windows)

```json
{
  "mcpServers": {
    "odoo-llm-mcp-server": {
      "type": "stdio",
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://localhost:8069/mcp",
        "--header",
        "Authorization: Bearer YOUR_API_KEY_HERE"
      ],
      "env": {
        "MCP_TRANSPORT": "streamable-http"
      }
    }
  }
}
```

**⚠️ Important**: Replace `YOUR_API_KEY_HERE` with your actual API key from the Odoo MCP Server configuration.

### Testing the Connection

After adding the configuration to Claude Desktop:

1. **Restart Claude Desktop**
2. **Start a new conversation**
3. **Type**: "What tools do you have available?"
4. **Expected**: Claude should list your Odoo LLM tools

## Supported MCP Clients

### ✅ **Claude Desktop** (Verified)

Complete integration with Anthropic's Claude Desktop application using the configuration above.

### ✅ **Letta Agents** (Verified)

Full compatibility with Letta's MCP client for AI agent tool integration. Use our llm_letta module.

### 🔧 **Other MCP Client Libraries**

For any MCP-compatible client, configure them to connect to:

- **URL**: `http://your-odoo-server:8069/mcp`
- **Transport**: `streamable_http`
- **Authentication**: Bearer token with API key

## Security

- **API Key Authentication**: Integrated with Odoo's user system
- **Access Control**: Respects all Odoo permissions and ACL rules
- **User Context**: Tools execute with authenticated user's permissions
