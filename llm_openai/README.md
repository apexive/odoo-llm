# OpenAI Provider for Odoo LLM Integration

This module integrates OpenAI's API with the Odoo LLM framework, providing access to GPT models, embeddings, and other OpenAI services.

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
          │          ★ llm_openai (This Module) ★         │
          │              OpenAI Provider                  │
          │  GPT-4o │ GPT-4 │ GPT-3.5 │ DALL-E │ Embeddings │
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

**For AI chat with OpenAI:**

```bash
odoo-bin -d your_db -i llm_assistant,llm_openai
```

### Auto-Installed Dependencies

- `llm` (core infrastructure)

### Alternative Providers

| Instead of OpenAI | Use        | Best For              |
| ----------------- | ---------- | --------------------- |
| `llm_ollama`      | Local AI   | Privacy, no API costs |
| `llm_mistral`     | Mistral AI | European, fast        |
| `llm_replicate`   | Replicate  | Image generation      |

### Common Setups

| I want to...          | Install                                  |
| --------------------- | ---------------------------------------- |
| Chat with GPT-4       | `llm_assistant` + `llm_openai`           |
| GPT + document search | Above + `llm_knowledge` + `llm_pgvector` |
| GPT + external tools  | Above + `llm_mcp_server`                 |

## Features

- Connect to OpenAI API with proper authentication
- Support for all OpenAI models (GPT-4o, GPT-4, GPT-3.5, etc.)
- Text embeddings support
- Function calling capabilities
- Multimodal (vision) capabilities for GPT-4o and GPT-4 Vision
- Automatic model discovery

## Multimodal Support (Vision)

GPT-4o and GPT-4 Vision models support image and PDF analysis.

### How to Use

Attach files to your chat message - they're automatically processed:

| Type   | OpenAI Format                     |
| ------ | --------------------------------- |
| Images | `type: "image_url"` with data URL |
| PDFs   | `type: "file"` with file_data     |
| Text   | Appended to message content       |

### Supported Image Formats

- JPEG, PNG, GIF, WebP

### Example

```python
# Analyze an image
thread.message_post(
    body="Describe this image",
    attachment_ids=[(4, image_id)]
)
```

**Note:** Requires a multimodal-capable model (GPT-4o, GPT-4 Vision).

## Configuration

1. Install the module
2. Navigate to **LLM > Configuration > Providers**
3. Create a new provider and select "OpenAI" as the provider type
4. Enter your OpenAI API key
5. Click "Fetch Models" to import available models

## OpenAI-Compatible Endpoints

Many AI providers offer OpenAI-compatible endpoints, allowing you to use the same code and configuration with different services. This module supports connecting to any of these compatible endpoints by changing the base URL in the provider configuration.

### Supported OpenAI-Compatible Endpoints

| Provider   | Base URL                                                 | Models                             | Notes                               |
| ---------- | -------------------------------------------------------- | ---------------------------------- | ----------------------------------- |
| OpenAI     | https://api.openai.com/v1/                               | GPT-4o, GPT-4, GPT-3.5 Turbo, etc. | Official OpenAI API                 |
| Anthropic  | https://api.anthropic.com/v1/                            | Claude 3 Opus, Sonnet, Haiku       | Requires Anthropic API key          |
| DeepSeek   | https://api.deepseek.com/v1/                             | DeepSeek-Coder, DeepSeek-Chat      | Requires DeepSeek API key           |
| Ollama     | http://localhost:11434/v1/                               | Llama, Mistral, Vicuna, etc.       | Local deployment, no API key needed |
| Google AI  | https://generativelanguage.googleapis.com/v1beta/openai/ | Gemini models                      | Requires Google API key             |
| Mistral AI | https://api.mistral.ai/v1/                               | Mistral-7B, Mixtral-8x7B, etc.     | Requires Mistral AI API key         |

### Using OpenAI-Compatible Endpoints

To use an alternative provider with an OpenAI-compatible endpoint:

1. Create a new provider in **LLM > Configuration > Providers**
2. Select "OpenAI" as the provider type
3. Enter your API key for the specific provider
4. Set the "Base URL" field to the appropriate endpoint URL from the table above
5. Click "Fetch Models" to discover available models

## Technical Details

This module extends the base LLM integration framework with OpenAI-specific implementations:

- Implements the OpenAI API client with proper authentication and error handling
- Provides model mapping and conversion between OpenAI formats and Odoo LLM formats
- Handles rate limiting and retries according to OpenAI best practices

## Dependencies

- llm (LLM Integration Base)

## License

LGPL-3
