# LLM ComfyICU Integration

This module integrates Odoo with the ComfyICU API for media generation capabilities.

**Module Type:** 🔧 Provider (Cloud ComfyUI)

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
          │       ★ llm_comfy_icu (This Module) ★     │
          │          ComfyICU Cloud Provider          │
          │  ☁️ Cloud │ No GPU Required │ Managed     │
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

**For cloud-based ComfyUI:**

```bash
odoo-bin -d your_db -i llm_comfy_icu
```

### Auto-Installed Dependencies

- `llm` (core infrastructure)

### ComfyUI vs ComfyICU

| Feature     | llm_comfyui    | llm_comfy_icu |
| ----------- | -------------- | ------------- |
| **Hosting** | 🖥️ Self-hosted | ☁️ Cloud      |
| **GPU**     | Required       | Not needed    |
| **Setup**   | Complex        | Easy          |
| **Cost**    | Hardware       | Pay-per-use   |

### Common Setups

| I want to...           | Install                                          |
| ---------------------- | ------------------------------------------------ |
| Cloud image generation | `llm_comfy_icu`                                  |
| Chat + cloud images    | `llm_assistant` + `llm_openai` + `llm_comfy_icu` |

## Features

- Adds ComfyICU as a provider option in the LLM framework
- Supports media generation through ComfyICU workflows
- Follows the same provider model pattern as other LLM integrations

## Configuration

1. Install the module
2. Create a provider with type "ComfyICU"
3. Configure the API key
4. Create models with the appropriate workflow IDs

## Security

This module follows the standard two-tier security model:

- Regular users (base.group_user) have read-only access to models
- LLM Managers (llm.group_llm_manager) have full CRUD access
