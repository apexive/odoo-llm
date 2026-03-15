# LLM pgvector Integration

PostgreSQL-native vector storage using pgvector extension.

**Module Type:** 🗄️ Vector Store (PostgreSQL Native)

## Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                    Used By (RAG Modules)                      │
│        ┌───────────────┐           ┌───────────────┐         │
│        │ llm_knowledge │           │llm_assistant  │         │
│        │   (RAG)       │           │  (with RAG)   │         │
│        └───────┬───────┘           └───────┬───────┘         │
└────────────────┼───────────────────────────┼─────────────────┘
                 └─────────────┬─────────────┘
                               ▼
              ┌───────────────────────────────────────────┐
              │             llm_store                     │
              │        (Vector Store API)                 │
              └─────────────────────┬─────────────────────┘
                                    │
                                    ▼
              ┌───────────────────────────────────────────┐
              │      ★ llm_pgvector (This Module) ★       │
              │         pgvector Implementation           │
              │  🐘 PostgreSQL │ Native │ No Extra Server │
              └─────────────────────┬─────────────────────┘
                                    │
                                    ▼
              ┌───────────────────────────────────────────┐
              │             PostgreSQL + pgvector         │
              │           (Your Odoo Database)            │
              └───────────────────────────────────────────┘
```

## Installation

### What to Install

**For RAG with PostgreSQL vectors:**

```bash
# 1. Install pgvector extension on PostgreSQL
# See: https://github.com/pgvector/pgvector

# 2. Install the Odoo module
odoo-bin -d your_db -i llm_knowledge,llm_pgvector
```

### Auto-Installed Dependencies

- `llm` (core infrastructure)
- `llm_store` (vector store abstraction)

### Why Choose pgvector?

| Feature          | pgvector                      |
| ---------------- | ----------------------------- |
| **Integration**  | 🐘 Uses your Odoo PostgreSQL  |
| **Extra Server** | ❌ Not needed                 |
| **Simplicity**   | ✅ No external dependencies   |
| **Scale**        | 📊 Good for moderate datasets |

### Vector Store Comparison

| Feature      | llm_pgvector  | llm_qdrant       | llm_chroma       |
| ------------ | ------------- | ---------------- | ---------------- |
| **Server**   | 🐘 PostgreSQL | 🔷 Qdrant server | 🌈 Chroma server |
| **Setup**    | Easy          | Moderate         | Moderate         |
| **Scale**    | Medium        | High             | Medium           |
| **Best For** | Simple RAG    | Large scale      | Development      |

### Common Setups

| I want to... | Install                                                           |
| ------------ | ----------------------------------------------------------------- |
| Simple RAG   | `llm_knowledge` + `llm_pgvector`                                  |
| Chat + RAG   | `llm_assistant` + `llm_openai` + `llm_knowledge` + `llm_pgvector` |

## Features

- Native PostgreSQL vector storage
- Cosine similarity search
- Collection-specific indices
- Metadata filtering
- Uses existing Odoo database connection

## Configuration

1. Ensure pgvector extension is installed on your PostgreSQL server
2. Install the module
3. Configure vector store in **LLM > Configuration > Vector Stores**
4. Set up knowledge base with pgvector as the storage backend

## Creating Indices for Better Performance

Models inheriting from `EmbeddingMixin` can organize their embeddings into collections and create collection-specific indices:

```python
class DocumentChunk(models.Model):
    _name = 'document.chunk'
    _inherit = ['llm.embedding.mixin']

    def ensure_collection_index(self, collection_id=None):
        """Ensure a vector index exists for the specified collection."""
        embedding_model = self.env['llm.model'].search([
            ('model_use', '=', 'embedding'),
        ], limit=1)

        sample_embedding = embedding_model.generate_embedding("")
        dimensions = len(sample_embedding)

        self.create_embedding_index(
            collection_id=collection_id,
            dimensions=dimensions,
            force=False
        )
```

## Requirements

- Odoo 18.0+
- PostgreSQL with pgvector extension
- Python packages: `pgvector`, `numpy`

## License

LGPL-3
