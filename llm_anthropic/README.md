# Anthropic Provider for Odoo LLM Integration

This module integrates Anthropic's Claude API with the Odoo LLM framework, providing access to Claude models for chat, tool calling, and extended thinking capabilities.

**Module Type:** 🔧 Provider

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Used By (Any LLM Module)                     │
│  ┌─────────────┐  ┌───────────┐  ┌─────────────┐  ┌───────────┐ │
│  │llm_assistant│  │llm_thread │  │llm_knowledge│  │llm_generate│ │
│  └──────┬──────┘  └─────┬─────┘  └──────┬──────┘  └─────┬─────┘ │
└─────────┼───────────────┼───────────────┼───────────────┼───────┘
          │               │               │               │
          └───────────────┴───────┬───────┴───────────────┘
                                  ▼
          ┌───────────────────────────────────────────────┐
          │        ★ llm_anthropic (This Module) ★        │
          │              Anthropic Provider               │
          │  Claude 4.5 │ Claude 4 │ Claude 3.x │ Vision  │
          └─────────────────────┬─────────────────────────┘
                                │
                                ▼
          ┌───────────────────────────────────────────────┐
          │                    llm                        │
          │              (Core Base Module)               │
          └───────────────────────────────────────────────┘
```

## Installation

### What to Install

**For AI chat with Claude:**

```bash
odoo-bin -d your_db -i llm_assistant,llm_anthropic
```

### Auto-Installed Dependencies

- `llm` (core infrastructure)
- `llm_tool` (tool/function calling support)

### Alternative Providers

| Instead of Anthropic | Use        | Best For              |
| -------------------- | ---------- | --------------------- |
| `llm_openai`         | OpenAI     | GPT models, DALL-E    |
| `llm_ollama`         | Local AI   | Privacy, no API costs |
| `llm_mistral`        | Mistral AI | European, fast        |

### Common Setups

| I want to...             | Install                                  |
| ------------------------ | ---------------------------------------- |
| Chat with Claude         | `llm_assistant` + `llm_anthropic`        |
| Claude + document search | Above + `llm_knowledge` + `llm_pgvector` |
| Claude + external tools  | Above + `llm_mcp_server`                 |

## Features

- Connect to Anthropic API with proper authentication
- Support for all Claude models (4.5, 4, 3.x series)
- Tool/function calling capabilities
- Extended thinking support (Claude's reasoning mode)
- Streaming responses
- Multimodal (vision) capabilities for supported models
- Automatic model discovery

## Multimodal Support

Claude models support sending images and PDFs along with text messages.

### How to Use

1. Attach files (images, PDFs, text files) to your chat message
2. The module automatically:
   - Converts images to base64 for Claude's vision API
   - Sends PDFs as document blocks
   - Includes text file contents in the message

### Supported Formats

| Type   | Formats                           | Claude Format                         |
| ------ | --------------------------------- | ------------------------------------- |
| Images | JPEG, PNG, GIF, WebP              | `type: "image"` with base64 source    |
| PDFs   | application/pdf                   | `type: "document"` with base64 source |
| Text   | .txt, .md, .csv, .py, .json, etc. | Appended to message text              |

### Example

```python
# Attach an image to the chat thread
thread.message_post(
    body="What's in this image?",
    attachment_ids=[(4, image_attachment.id)]
)
# Claude will analyze the image and respond
```

**Note:** Non-multimodal models (like older Claude versions) will skip images/PDFs automatically.

## Configuration

1. Install the module
2. Navigate to **LLM > Configuration > Providers**
3. Create a new provider and select "Anthropic" as the provider type
4. Enter your Anthropic API key
5. Click "Fetch Models" to import available models

## Supported Models

| Model Family | Models              | Capabilities                           |
| ------------ | ------------------- | -------------------------------------- |
| Claude 4.5   | Opus, Sonnet, Haiku | Chat, Vision, Tools, Extended Thinking |
| Claude 4     | Opus, Sonnet        | Chat, Vision, Tools                    |
| Claude 3.x   | Opus, Sonnet, Haiku | Chat, Vision, Tools                    |

## Technical Details

This module extends the base LLM integration framework with Anthropic-specific implementations:

### Key Differences from OpenAI

| Aspect           | OpenAI                                    | Anthropic                                 |
| ---------------- | ----------------------------------------- | ----------------------------------------- |
| System message   | In messages array                         | Separate `system` parameter               |
| Tool format      | `{"type": "function", "function": {...}}` | `{"name", "description", "input_schema"}` |
| Response content | Single string                             | Array of content blocks                   |
| Tool results     | `role: "tool"`                            | `role: "user"` + `type: "tool_result"`    |

### Extended Thinking

Claude supports extended thinking mode, which allows the model to show its reasoning process:

```python
# Enable extended thinking in your assistant configuration
response = provider.chat(
    messages=messages,
    extended_thinking=True,
    thinking_budget=10000  # tokens for reasoning
)
```

### Implemented Methods

- `anthropic_get_client()` - Initialize Anthropic client
- `anthropic_chat()` - Chat with tool calling and streaming support
- `anthropic_format_tools()` - Convert tools to Anthropic format
- `anthropic_format_messages()` - Format mail.message records
- `anthropic_models()` - List available Claude models
- `anthropic_normalize_prepend_messages()` - Handle prepend messages

## Dependencies

- `llm` (LLM Integration Base)
- `llm_tool` (Tool Calling Support)
- Python: `anthropic` package

## Contributors

- Crottolo <bo@fl1.cz> - Odoo 18.0 port with full tool calling and extended thinking support

## License

LGPL-3
