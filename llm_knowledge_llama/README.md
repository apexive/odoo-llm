# LLM Knowledge LlamaIndex Integration

LlamaIndex integration for advanced knowledge processing and RAG capabilities.

**Module Type:** 🔌 Extension (Advanced RAG)

## Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                      Application Layer                        │
│                    ┌───────────────┐                          │
│                    │ llm_assistant │                          │
│                    └───────┬───────┘                          │
└────────────────────────────┼──────────────────────────────────┘
                             │
                             ▼
┌───────────────────────────────────────────────────────────────┐
│                      Knowledge Layer                          │
│        ┌───────────────────────────────────────────┐         │
│        │            llm_knowledge (RAG)            │         │
│        └─────────────────────┬─────────────────────┘         │
└──────────────────────────────┼────────────────────────────────┘
                               │
                               ▼
              ┌───────────────────────────────────────────┐
              │  ★ llm_knowledge_llama (This Module) ★    │
              │        LlamaIndex Integration             │
              │  📚 Advanced Chunking │ Query Optimizer   │
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

**For advanced RAG with LlamaIndex:**

```bash
# Install Python dependencies
pip install llama_index nltk

# Install the Odoo module
odoo-bin -d your_db -i llm_knowledge_llama
```

### Auto-Installed Dependencies

- `llm` (core infrastructure)
- `llm_knowledge` (RAG infrastructure)

### Why Choose LlamaIndex?

| Feature        | LlamaIndex                    |
| -------------- | ----------------------------- |
| **Chunking**   | 📚 Advanced document chunking |
| **Embeddings** | 🎯 Enhanced embedding support |
| **Queries**    | ⚡ Query optimization         |
| **Processing** | 🔄 Smart document processing  |

### Common Setups

| I want to...        | Install                                                                 |
| ------------------- | ----------------------------------------------------------------------- |
| Advanced RAG        | `llm_knowledge_llama` + `llm_pgvector`                                  |
| Chat + advanced RAG | `llm_assistant` + `llm_openai` + `llm_knowledge_llama` + `llm_pgvector` |

## Features

- LlamaIndex document processing
- Advanced chunking strategies
- Enhanced embedding support
- Query optimization
- Smart document splitting

## Configuration

Configure LlamaIndex-specific settings in knowledge base configuration.

## Requirements

- Odoo 18.0+
- `llm_knowledge` module
- Python packages: `llama_index`, `nltk`

## License

LGPL-3
