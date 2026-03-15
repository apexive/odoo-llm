# Replicate Provider for Odoo LLM Integration

This module integrates Replicate's API with the Odoo LLM framework, providing access to a diverse range of AI models.

**Module Type:** 🔧 Provider (Image Generation)

## Architecture

```
┌───────────────────────────────────────────────────────┐
│             Used By (Generation Modules)              │
│     ┌─────────────┐           ┌───────────┐          │
│     │llm_assistant│           │llm_generate│          │
│     └──────┬──────┘           └─────┬─────┘          │
└────────────┼────────────────────────┼────────────────┘
             └────────────┬───────────┘
                          ▼
          ┌───────────────────────────────────────────┐
          │       ★ llm_replicate (This Module) ★     │
          │          Replicate.com Provider           │
          │  🖼️ SDXL │ Flux │ Llama │ Model Marketplace │
          └─────────────────────┬─────────────────────┘
                                │
                                ▼
          ┌───────────────────────────────────────────┐
          │                   llm                     │
          │            (Core Base Module)             │
          └───────────────────────────────────────────┘
```

## Installation

### What to Install

**For image generation:**

```bash
odoo-bin -d your_db -i llm_assistant,llm_replicate
```

### Auto-Installed Dependencies

- `llm` (core infrastructure)

### When to Use Replicate

| Use Case          | Replicate                |
| ----------------- | ------------------------ |
| **Model Variety** | 🎯 Huge marketplace      |
| **Image Gen**     | ✅ SDXL, Flux, etc.      |
| **Pay-per-use**   | 💳 Pay only what you use |

### Common Setups

| I want to...    | Install                                          |
| --------------- | ------------------------------------------------ |
| Generate images | `llm_assistant` + `llm_replicate`                |
| Chat + images   | `llm_assistant` + `llm_openai` + `llm_replicate` |

## Features

- Connect to Replicate API with proper authentication
- Support for various AI models hosted on Replicate
- Text generation capabilities
- Automatic model discovery

## Configuration

1. Install the module
2. Navigate to **LLM > Configuration > Providers**
3. Create a new provider and select "Replicate" as the provider type
4. Enter your Replicate API key
5. Click "Fetch Models" to import available models

## Current Status

This module is in an early stage of development. Basic functionality for connecting to Replicate's API and generating text with various models is implemented, but advanced features are still under development.

## Technical Details

This module extends the base LLM integration framework with Replicate-specific implementations:

- Implements the Replicate API client with proper authentication
- Provides model mapping between Replicate formats and Odoo LLM formats
- Handles basic error cases

## Dependencies

- llm (LLM Integration Base)

## License

LGPL-3
