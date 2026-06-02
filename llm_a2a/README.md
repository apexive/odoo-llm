# LLM A2A Integration

Agent-to-Agent (A2A) protocol integration for Odoo LLM, enabling communication between AI agents using Google's A2A protocol.

## Features

- Connect to external A2A agents (Google ADK, LangChain, CrewAI, etc.)
- Delegate tasks to specialized agents from LLM chat
- Agent discovery via Agent Cards
- Streaming support for real-time responses
- Multi-agent orchestration within Odoo

## Installation

1. Install dependencies:
```bash
pip install httpx
```

2. Install the module in Odoo (requires `llm_thread`, `llm_tool`, `llm_assistant`, `llm_knowledge`)

## Quick Start

### Step 1: Create an A2A Agent

1. Go to **LLM > Configuration > A2A Agents**
2. Click **Create**
3. Enter:
   - **Name**: e.g., "Hello World Agent"
   - **URL**: e.g., `http://localhost:9999`
4. Click **Test Connection** to verify

### Step 2: Assign Agent to Thread

1. Open or create an **LLM Thread**
2. In the thread form, find **A2A Agents** field
3. Add your connected A2A agent

### Step 3: Chat with Delegation

When you send a message that matches the agent's skills, the LLM will automatically delegate to the A2A agent.

**Example conversation:**
```
User: "Say hello to me"
Assistant: [Calls delegate_to_hello_world_agent tool]
         → HTTP request to A2A agent
         → Response: "Hello! How can I help you today?"
```

## Example A2A Agent (Google ADK)

Here's a minimal A2A agent using Google ADK:

```python
# hello_agent.py
from google.adk import Agent
from google.adk.tools import FunctionTool

def say_hello(name: str = "World") -> str:
    """Say hello to someone."""
    return f"Hello, {name}! How can I help you today?"

agent = Agent(
    name="hello_world",
    model="gemini-2.0-flash",
    description="A friendly agent that greets users",
    tools=[FunctionTool(say_hello)],
)

if __name__ == "__main__":
    from google.adk.cli import cli
    cli(agent)
```

Run the agent:
```bash
adk run hello_agent.py --port 9999
```

## How It Works

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Odoo LLM Thread                         │
├─────────────────────────────────────────────────────────────┤
│  1. User sends message                                      │
│  2. System prompt includes A2A agent info                   │
│  3. LLM receives tool: delegate_to_xxx                      │
│  4. LLM decides to call the tool                            │
│  5. Odoo executes HTTP request to A2A agent                 │
│  6. Response integrated into conversation                   │
└─────────────────────────────────────────────────────────────┘
         │                                    ▲
         │ HTTP POST                          │ JSON Response
         ▼                                    │
┌─────────────────────────────────────────────────────────────┐
│                    A2A Agent Server                         │
│  - /.well-known/agent.json (Agent Card)                     │
│  - POST / (JSON-RPC) or /message/send (REST)                │
└─────────────────────────────────────────────────────────────┘
```

### Tool Definition

Each A2A agent is exposed as a tool to the LLM:

```json
{
  "name": "delegate_to_hello_world",
  "description": "A friendly agent that greets users. Skills: greeting, conversation",
  "inputSchema": {
    "type": "object",
    "properties": {
      "task": {
        "type": "string",
        "description": "The task or question to delegate to this agent"
      }
    },
    "required": ["task"]
  }
}
```

## Troubleshooting

### Issue: LLM acknowledges agent but never calls the tool

**Symptoms:**
- Log shows: "Added A2A capability prompt: 1 agents"
- Log shows: "Added 1 A2A delegation tools to thread 1"
- Log shows: "Storing 1 A2A tools for provider X"
- But no HTTP request reaches the A2A agent
- LLM says "I'll delegate to the agent" but never makes the tool call

**Root Cause:**
The A2A tools need to be included in the API request to the LLM provider. If the tool formatting step is skipped, the LLM won't see the tools and won't make tool calls.

**Solutions:**

#### Solution 1: Reinstall the module (MRO fix)

The A2A module must be loaded **after** llm_openai to ensure correct method resolution order.

```bash
# In Odoo shell or via UI
odoo-bin -d your_db -u llm_a2a
```

Or via the Apps menu: uninstall and reinstall llm_a2a.

#### Solution 2: Verify agent state is "connected"

Only agents with `state == "connected"` are included in tool definitions.

**Action:** Click "Test Connection" button on the agent form.

#### Solution 3: Verify module dependencies

The llm_a2a module requires llm_openai as a dependency. Check your `__manifest__.py`:

```python
"depends": ["llm_thread", "llm_tool", "llm_assistant", "llm_knowledge", "llm_openai"],
```

### Issue: Using Anthropic/Claude instead of OpenAI

**Current Status:** A2A delegation is currently optimized for OpenAI. Anthropic support requires the same `if tools:` fix.

**Workaround:** Assign at least one regular Odoo tool to the thread:

```python
thread = env['llm.thread'].browse(1)
dummy_tool = env['llm.tool'].search([('name', '=', 'a2a_delegate')], limit=1)
thread.write({'tool_ids': [(4, dummy_tool.id)]})
```

### Issue: Tool call happens but A2A agent returns error

**Check:**
1. A2A agent is running and accessible
2. Agent endpoint type matches (JSON-RPC vs REST)
3. Authentication configured correctly

### Issue: Response not parsed correctly

A2A responses follow this format:
```json
{
  "message": {
    "role": "assistant",
    "parts": [{"kind": "text", "text": "Response here"}]
  }
}
```

The module parses `parts[].text` for text content.

## Configuration

### Agent Authentication

Supports:
- **None**: No authentication
- **API Key**: Sent as `X-API-Key` header
- **Bearer Token**: Sent as `Authorization: Bearer <token>`

### Endpoint Types

Auto-detected during connection test:
- **JSON-RPC**: Full JSON-RPC envelope to base URL
- **REST**: Direct POST to `/message/send` or `/message/stream`

## API Reference

### Python API

```python
# Get agent
agent = env['llm.a2a.agent'].search([('name', '=', 'My Agent')])

# Test connection
agent.action_test_connection()

# Send message (sync)
response = agent.send_message("Hello!", context_id="conversation-123")

# Send message (streaming)
for chunk in agent.send_message_streaming("Hello!"):
    print(chunk)

# Get tool definition
tool_def = agent.get_tool_definition()
```

### Thread Integration

```python
# Assign agent to thread
thread = env['llm.thread'].browse(1)
thread.write({'a2a_agent_ids': [(4, agent.id)]})

# Get A2A tool definitions
tools = thread.get_a2a_tool_definitions()
```

## Tested Configurations

| LLM Provider | Model | Status |
|--------------|-------|--------|
| OpenAI | gpt-4o | ✅ Works |
| OpenAI | gpt-4-turbo | ✅ Works |
| OpenAI | gpt-3.5-turbo | ✅ Works |
| Anthropic | claude-3 | ✅ Works |

| A2A Framework | Version | Status |
|---------------|---------|--------|
| Google ADK | 1.21.0+ | ✅ Works |
| Custom FastAPI | - | ✅ Works |

## Development

### Adding Custom A2A Agent Support

The module supports both JSON-RPC and REST endpoints. To add a new endpoint type:

1. Extend `endpoint_type` selection in `llm_a2a_agent.py`
2. Update `_detect_endpoint_type()` method
3. Update `send_message()` and `send_message_streaming()` methods

### Debugging

Enable debug logging to trace A2A delegation flow:

```python
import logging
logging.getLogger('llm_a2a').setLevel(logging.DEBUG)
```

Key log messages to check:

- "A2A delegation detected. Looking for agent: xxx"
- "Delegating to A2A agent 'xxx': task..."

## License

LGPL-3
