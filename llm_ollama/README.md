# Ollama Provider for Odoo LLM Integration

This module integrates Ollama with the Odoo LLM framework, providing access to locally deployed open-source models.

**Module Type:** 🔧 Provider (Local/Privacy-Focused)

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
          │          ★ llm_ollama (This Module) ★         │
          │           Ollama Provider (Local AI)          │
          │  🔒 Llama 3 │ Mistral │ CodeLlama │ Phi │ etc │
          └─────────────────────┬─────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
┌───────────────────────────┐   ┌───────────────────────────┐
│           llm             │   │      Ollama Server        │
│    (Core Base Module)     │   │   (localhost:11434)       │
└───────────────────────────┘   │   🖥️ Runs on your hardware │
                                └───────────────────────────┘
```

## Installation

### What to Install

**For local AI chat (no external API):**

```bash
# 1. Install Ollama on your server first
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3

# 2. Install the Odoo module
odoo-bin -d your_db -i llm_assistant,llm_ollama
```

### Auto-Installed Dependencies

- `llm` (core infrastructure)

### Why Choose Ollama?

| Feature     | Ollama                  | Cloud Providers      |
| ----------- | ----------------------- | -------------------- |
| **Privacy** | 🔒 Data stays local     | ☁️ Sent to cloud     |
| **Cost**    | 💰 Free (your hardware) | 💳 Pay per token     |
| **Speed**   | ⚡ Depends on GPU       | ⚡ Generally fast    |
| **Offline** | ✅ Works offline        | ❌ Requires internet |

### Common Setups

| I want to...          | Install                                  |
| --------------------- | ---------------------------------------- |
| Local AI chat         | `llm_assistant` + `llm_ollama`           |
| Local AI + RAG        | Above + `llm_knowledge` + `llm_pgvector` |
| Mixed (local + cloud) | Install both `llm_ollama` + `llm_openai` |

## Features

- Connect to Ollama with proper configuration
- Support for various open-source models (Llama, Mistral, Vicuna, etc.)
- Text generation capabilities
- Function calling support
- Automatic model discovery
- Local deployment for privacy and control

## Configuration

1. Install the module
2. Set up Ollama on your server or local machine
3. Navigate to **LLM > Configuration > Providers**
4. Create a new provider and select "Ollama" as the provider type
5. Enter your Ollama server URL (default: http://localhost:11434)
6. Click "Fetch Models" to import available models

## Technical Details

This module extends the base LLM integration framework with Ollama-specific implementations:

- Implements the Ollama API client with proper configuration
- Provides model mapping between Ollama formats and Odoo LLM formats
- Supports function calling capabilities
- Handles streaming responses

## Dependencies

- llm (LLM Integration Base)
- llm_tool (LLM Tool Support)
- llm_mail_message_subtypes

## License

LGPL-3
