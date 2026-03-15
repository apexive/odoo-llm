# Letta LLM Integration

**Module Type:** 🔌 Extension (Stateful AI Agents)

## Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                      Application Layer                        │
│        ┌───────────────┐           ┌───────────────┐         │
│        │ llm_assistant │           │  llm_thread   │         │
│        └───────┬───────┘           └───────┬───────┘         │
└────────────────┼───────────────────────────┼─────────────────┘
                 └─────────────┬─────────────┘
                               ▼
              ┌───────────────────────────────────────────┐
              │       ★ llm_letta (This Module) ★         │
              │           Letta AI Integration            │
              │  🧠 Memory │ MCP Tools │ Stateful Agents  │
              └─────────────────────┬─────────────────────┘
                        ┌───────────┴───────────┐
                        ▼                       ▼
    ┌───────────────────────────┐   ┌───────────────────────────┐
    │           llm             │   │       Letta Server        │
    │    (Core Base Module)     │   │ (localhost:8283 or Cloud) │
    └───────────────────────────┘   │  🧠 Persistent memory     │
                                    └───────────────────────────┘
```

## Installation

### What to Install

**For stateful AI agents:**

```bash
# Install Python client
pip install letta-client

# Start Letta server (Docker)
docker compose up letta -d

# Install the Odoo module
odoo-bin -d your_db -i llm_letta,llm_mcp_server
```

### Auto-Installed Dependencies

- `llm` (core infrastructure)
- `llm_thread` (conversation management)

### Why Choose Letta?

| Feature     | Letta                          |
| ----------- | ------------------------------ |
| **Memory**  | 🧠 Persistent across sessions  |
| **State**   | 💾 Stateful agents per thread  |
| **Tools**   | 🔧 MCP tool integration        |
| **Context** | 📚 Long-term context awareness |

### Common Setups

| I want to...    | Install                                          |
| --------------- | ------------------------------------------------ |
| Stateful agents | `llm_letta` + `llm_mcp_server`                   |
| Memory + tools  | `llm_assistant` + `llm_letta` + `llm_mcp_server` |

## Overview

This is a **foundational module** that integrates [Letta](https://www.letta.com/) agents with Odoo. Letta is an advanced AI agent framework with built-in persistent memory, allowing agents to maintain context across conversations.

**What makes Letta different from standard LLM providers?**

- **Persistent Memory**: Letta agents maintain their own conversation history and memory state on the server side
- **Stateful Agents**: Each Odoo thread gets its own dedicated Letta agent that persists across sessions
- **Tool Access**: Agents can access Odoo data through Model Context Protocol (MCP)

> **Note**: This is a foundational integration. Advanced features like viewing tool calls in Odoo, shared memory across threads, and memory block management UI are planned for future releases.

## Features

- **Agent Lifecycle Management**: Automatic creation, updating, and cleanup of Letta agents per thread
- **MCP Tool Integration**: Zero-config connection to Odoo's MCP server
- **Auto-sync Tools**: Thread tools automatically synchronized to Letta agents
- **Streaming Support**: Real-time response streaming
- **Flexible Deployment**: Works with both self-hosted Letta server and Letta Cloud
- **Security**: Automatic per-user API key generation for MCP authentication

## Requirements

### Server Requirements

- **Letta Server**: Version 0.16.0+ (required for official Stainless SDK compatibility)
  - Self-hosted via Docker (recommended)
  - Or Letta Cloud account
- **PostgreSQL**: With `pgvector` extension enabled
- **Odoo Modules**:
  - `llm_letta`: This module
  - `llm_mcp_server`: Required for tool access

### Python Requirements

- **Letta Python Client**: Official SDK from PyPI
  ```bash
  pip install letta-client
  ```

### Optional

- **OpenAI API Key**: For using OpenAI models
- **Ollama**: For local open-source models

## Installation

### Step 1: Install Python Client

```bash
pip install letta-client
```

### Step 2: Set Up Letta Server (Docker)

**1. Add to your `docker-compose.yml`:**

```yaml
services:
  letta:
    image: letta/letta:latest
    ports:
      - "8083:8083" # Web UI
      - "8283:8283" # API server
    env_file:
      - .env.letta
```

**2. Create Letta database with vector support:**

```bash
# Replace POSTGRES_USER with your PostgreSQL username
psql -U POSTGRES_USER postgres -c "CREATE DATABASE letta OWNER POSTGRES_USER"
psql -U POSTGRES_USER letta -c "CREATE EXTENSION vector"

# Example (if your postgres user is 'odoo'):
# psql -U odoo postgres -c "CREATE DATABASE letta OWNER odoo"
# psql -U odoo letta -c "CREATE EXTENSION vector"
```

**3. Create `.env.letta` configuration file:**

```bash
cat > .env.letta <<EOF
LETTA_PG_URI=postgresql://POSTGRES_USER:POSTGRES_PASSWORD@host.docker.internal:5432/letta
OPENAI_API_KEY=your_openai_api_key
OLLAMA_BASE_URL=http://host.docker.internal:11434  # Optional: for local models
EOF

# Example (if postgres user is 'odoo' with password 'odoo'):
# LETTA_PG_URI=postgresql://odoo:odoo@host.docker.internal:5432/letta
```

**4. Start Letta server:**

```bash
docker compose up letta -d
```

Server will be available at:

- API: `http://localhost:8283`
- Web UI: Access via https://app.letta.com/settings/organization/projects?view-mode=selfHosted

See [Letta docs](https://docs.letta.com/guides/selfhosting) for more details.

### Step 3: Configure MCP Server in Odoo

The MCP (Model Context Protocol) server allows Letta agents to access Odoo tools.

1. Go to: **LLM → Configuration → MCP Server**
2. Set **External URL**: `http://host.docker.internal:8069`
   - This allows Letta in Docker to access Odoo running on the host machine

### Step 4: Install Odoo Module

```bash
odoo-bin -d your_db -i llm_letta,llm_mcp_server
```

## Quick Start

**Get started in 5 minutes:**

1. Go to **LLM → Threads** → Create new thread
2. Select:
   - **Provider**: "Letta (Local)"
   - **Model**: Any available model
3. Start chatting!

**That's it!** The agent is automatically created with:

- Access to all your active Odoo tools
- Persistent memory across conversations
- Context awareness

## Configuration

### Local Server (Default)

The default "Letta (Local)" provider connects to `localhost:8283` - no API key needed.

This is perfect for:

- Development
- Self-hosted deployments
- Maximum privacy and control

### Letta Cloud

To use Letta Cloud instead of self-hosting:

1. Get API token from [Letta Cloud](https://app.letta.com)
2. In Odoo: Go to **LLM → Providers → "Letta (Cloud)"**
3. Configure:
   - **API Key**: Your Letta Cloud token
   - **Project Name**: Default is "default-project"
4. Use "Fetch Models" wizard to sync available models

## Tool Integration

### Zero-Configuration MCP Setup

Letta agents automatically connect to Odoo's MCP server:

- **API keys generated automatically** per user (no manual setup!)
- All active `llm.tool` records instantly available to agents
- Tools sync automatically when thread configuration changes

### Available Tool Operations

Through MCP integration, agents can:

- **CRUD operations**: Create, read, update, delete records
- **Method execution**: Call model methods with parameters
- **Model inspection**: Explore available models and fields

> **⚠️ Tool Compatibility Note**
>
> Letta enforces OpenAI's strict mode for tool schemas, which requires all objects to have `additionalProperties: false`. The following tools are **not compatible** with Letta:
>
> - `odoo_record_creator` - Uses free-form field objects
> - `odoo_record_updater` - Uses free-form values objects
> - `odoo_model_method_executor` - Uses free-form kwargs objects
>
> These tools work with other LLM providers (OpenAI, Anthropic, etc.) but cannot be used with Letta agents. All other tools in your Odoo instance will work normally.

For technical details, see `TECHNICAL_GUIDE.md`.

## Usage Examples

### Basic Conversation

Create a thread with Letta provider and start asking questions:

```
User: What are my pending sales orders?
Agent: [Uses tools to query sale.order model and returns results]
```

### Stateful Context

The agent remembers previous conversations:

```
Session 1:
User: My company focuses on solar energy solutions
Agent: Got it, I'll remember that

Session 2 (days later):
User: Show me relevant product categories
Agent: Based on your focus on solar energy solutions, here are...
```

### Tool Usage

Agents can perform actions:

```
User: Create a new customer named "Acme Corp" with email acme@example.com
Agent: [Uses create_record tool] Created customer with ID 123
```

## Troubleshooting

### Letta server not connecting

Check Docker logs:

```bash
docker logs letta
```

Verify server is running:

```bash
curl http://localhost:8283/v1/health
```

### Tools not available to agent

1. Verify `llm_mcp_server` module is installed
2. Check MCP server configuration in Odoo (LLM → Configuration → MCP Server)
3. Ensure External URL is correctly set to `http://host.docker.internal:8069`
4. Check that tools are active in LLM → Tools

### Tool execution fails with "Invalid schema" or "additionalProperties" error

This occurs when using incompatible tools with Letta. The error message looks like:

```
INVALID_ARGUMENT: Bad request to OpenAI: Error code: 400 -
'additionalProperties' is required to be supplied and to be false
```

**Solution:** Don't use these tools with Letta agents:

- `odoo_record_creator`
- `odoo_record_updater`
- `odoo_model_method_executor`

These tools work with other LLM providers but are incompatible with Letta's strict mode requirements. Use alternative tools like `odoo_record_retriever` and `odoo_model_inspector` instead.

### Agent not remembering context

- Verify PostgreSQL `pgvector` extension is installed in Letta database
- Check Letta server logs for memory-related errors
- Ensure database connection in `.env.letta` is correct

### Streaming not working

- Ensure you're using the official letta-client SDK (`pip install letta-client`)
- Check browser console for errors
- Verify Odoo is in development mode for detailed error logs

## Advanced Topics

### How Memory Works

Letta agents maintain their own conversation history and memory state on the Letta server side:

- **One Agent Per Thread**: Each Odoo thread creates a dedicated Letta agent (stored in `external_id`)
- **Server-Side Memory**: Agent memory is stored in PostgreSQL with pgvector extension on the Letta server
- **Only Latest Message Sent**: The integration sends only the latest user message - Letta maintains full conversation context internally
- **Memory Blocks**: Agents are initialized with default persona and human memory blocks

### Agent Lifecycle

- **Creation**: Automatically created when a new Letta thread is started
- **Updates**: Agent model and system prompt updated when thread configuration changes
- **Tool Sync**: Tools automatically synchronized when `tool_ids` changes
- **Cleanup**: Agent and API keys deleted when thread is deleted or provider changes

### MCP Server Architecture

The integration uses Odoo's MCP server to expose tools to Letta agents:

- API keys generated automatically per user for MCP authentication
- MCP server registered with Letta on first tool attachment
- Tools synced bidirectionally (attach new, detach removed)

For detailed technical documentation, see `TECHNICAL_GUIDE.md`.

## Roadmap

Future enhancements planned for this module:

- **Tool Call Visualization**: View tool calls and execution logs in Odoo UI
- **Memory Management UI**: Configure agent memory blocks (persona, human, etc.) from Odoo
- **Shared Memory**: Enable memory sharing across multiple threads
- **Memory Inspector**: Browse and edit agent memory state
- **Advanced Agent Config**: Fine-tune agent parameters (temperature, context window, etc.) from Odoo

Contributions and feature requests are welcome!

## Links

- [Letta Official Documentation](https://docs.letta.com/)
- [Letta GitHub Repository](https://github.com/letta-ai/letta)
- [Letta Python Client (PyPI)](https://pypi.org/project/letta-client/)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)

## Support

For issues and questions:

- Check `TECHNICAL_GUIDE.md` for detailed technical documentation
- Review Letta server logs: `docker logs letta`
- Check Odoo logs for integration errors
