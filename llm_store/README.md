# LLM Vector Store Base for Odoo

Comprehensive vector database abstraction layer providing unified interfaces for similarity search, embeddings storage, and RAG (Retrieval Augmented Generation) capabilities across multiple vector store providers.

**Module Type:** 📦 Infrastructure

![Architecture](static/description/llm_store_architecture.png)

## Installation

### What to Install

This module is typically **auto-installed** as a dependency. You rarely need to install it directly.

**For RAG/Knowledge Base features:**

```
llm_knowledge + llm_pgvector (or llm_qdrant/llm_chroma)
```

### Auto-Installed Dependencies

These are pulled in automatically:

- `llm` (core infrastructure)
- `mail` (Odoo messaging)

### Choose a Vector Store Implementation

| Module         | Best For                 | Requirements                 |
| -------------- | ------------------------ | ---------------------------- |
| `llm_pgvector` | Production (recommended) | PostgreSQL 14+ with pgvector |
| `llm_qdrant`   | Large-scale deployments  | Qdrant server                |
| `llm_chroma`   | Development/testing      | None (embedded)              |

### Common Setups Using This Module

| I want to...                   | Install                                                       |
| ------------------------------ | ------------------------------------------------------------- |
| Add RAG to my AI assistant     | `llm_knowledge` + `llm_pgvector` + `llm_assistant` + provider |
| Simple document search         | `llm_knowledge` + `llm_chroma`                                |
| High-performance vector search | `llm_knowledge` + `llm_qdrant`                                |

## Overview

The LLM Vector Store Base module serves as the foundation for vector database operations in the Odoo LLM ecosystem. It provides a provider-agnostic interface that enables seamless integration with various vector databases while maintaining consistent APIs and performance optimizations.

### Core Capabilities

- **Multi-Provider Support** - Unified interface for ChromaDB, pgvector, Qdrant, and other vector stores
- **Collection Management** - Abstract models for organizing and managing vector collections
- **Vector Operations** - Insert, search, update, and delete operations with metadata support
- **Index Management** - Automatic index creation and optimization for performance
- **RAG Integration** - Seamless integration with knowledge base and retrieval systems

## Key Features

### Provider Abstraction Framework

**Unified Interface Across Vector Stores:**

```python
class LLMStore(models.Model):
    _name = "llm.store"
    _inherit = ["mail.thread"]
    _description = "LLM Vector Store"

    def _dispatch(self, method, *args, **kwargs):
        """Dynamic dispatch to service-specific implementation"""
        service_method = f"{self.service}_{method}"
        if hasattr(self, service_method):
            return getattr(self, service_method)(*args, **kwargs)
        else:
            raise NotImplementedError(f"Method {method} not implemented for {self.service}")
```

**Supported Vector Store Providers:**

- **ChromaDB** (`llm_chroma`) - HTTP client integration with persistent storage
- **pgvector** (`llm_pgvector`) - PostgreSQL extension for native SQL vector operations
- **Qdrant** (`llm_qdrant`) - High-performance vector search engine
- **Extensible Architecture** - Easy addition of new vector store providers

### Collection Management

**Abstract Collection Model:**

```python
class LLMStoreCollection(models.Model):
    _name = "llm.store.collection"
    _description = "Vector Store Collection"

    name = fields.Char(required=True)
    store_id = fields.Many2one('llm.store', required=True)
    dimension = fields.Integer(required=True)
    distance_metric = fields.Selection([
        ('cosine', 'Cosine Similarity'),
        ('euclidean', 'Euclidean Distance'),
        ('dot_product', 'Dot Product')
    ], default='cosine')

    def create_collection(self):
        """Create collection in vector store"""
        return self.store_id._dispatch('create_collection',
                                     name=self.name,
                                     dimension=self.dimension,
                                     metric=self.distance_metric)

    def insert_vectors(self, vectors, metadata=None, ids=None):
        """Insert vectors with optional metadata"""
        return self.store_id._dispatch('insert_vectors',
                                     collection=self.name,
                                     vectors=vectors,
                                     metadata=metadata,
                                     ids=ids)

    def search_vectors(self, query_vector, limit=10, filter_metadata=None):
        """Search similar vectors"""
        return self.store_id._dispatch('search_vectors',
                                     collection=self.name,
                                     query_vector=query_vector,
                                     limit=limit,
                                     filter=filter_metadata)
```

### Vector Operations

#### Insert Operations

```python
# Single vector insertion
collection.insert_vectors(
    vectors=[[0.1, 0.2, 0.3, ...]],  # Single embedding
    metadata=[{'document_id': 123, 'chunk_index': 0}],
    ids=['doc_123_chunk_0']
)

# Batch vector insertion
collection.insert_vectors(
    vectors=[
        [0.1, 0.2, 0.3, ...],  # Document 1, chunk 1
        [0.4, 0.5, 0.6, ...],  # Document 1, chunk 2
        [0.7, 0.8, 0.9, ...]   # Document 2, chunk 1
    ],
    metadata=[
        {'document_id': 123, 'chunk_index': 0, 'text': 'First chunk...'},
        {'document_id': 123, 'chunk_index': 1, 'text': 'Second chunk...'},
        {'document_id': 124, 'chunk_index': 0, 'text': 'Another doc...'}
    ],
    ids=['doc_123_chunk_0', 'doc_123_chunk_1', 'doc_124_chunk_0']
)
```

#### Search Operations

```python
# Basic similarity search
results = collection.search_vectors(
    query_vector=[0.2, 0.3, 0.4, ...],  # Query embedding
    limit=5
)

# Search with metadata filtering
filtered_results = collection.search_vectors(
    query_vector=[0.2, 0.3, 0.4, ...],
    limit=10,
    filter_metadata={
        'document_type': 'manual',
        'language': 'en',
        'category': 'technical'
    }
)

# Search with complex filters
complex_results = collection.search_vectors(
    query_vector=[0.2, 0.3, 0.4, ...],
    limit=20,
    filter_metadata={
        '$and': [
            {'document_id': {'$in': [123, 124, 125]}},
            {'confidence_score': {'$gte': 0.8}},
            {'$or': [
                {'language': 'en'},
                {'language': 'es'}
            ]}
        ]
    }
)
```

## RAG Integration Examples

### Knowledge Base Search

```python
class KnowledgeSearchTool(models.Model):
    _name = "llm.tool.knowledge.search"
    _inherit = "llm.tool"

    def knowledge_search_execute(self, query, collection_id=None, limit=5):
        """Search knowledge base using vector similarity"""

        # Get embedding for query
        embedding_model = self.env['llm.model'].search([
            ('model_use', '=', 'embedding'),
            ('default', '=', True)
        ], limit=1)

        query_embedding = embedding_model.provider_id.embedding(
            text=query,
            model=embedding_model.name
        )

        # Search in vector store
        if collection_id:
            collection = self.env['llm.knowledge.collection'].browse(collection_id)
        else:
            collection = self.env['llm.knowledge.collection'].search([], limit=1)

        if not collection or not collection.store_collection_id:
            return {'error': 'No vector collection available'}

        # Perform similarity search
        results = collection.store_collection_id.search_vectors(
            query_vector=query_embedding,
            limit=limit,
            filter_metadata={'active': True}
        )

        # Format results for LLM consumption
        formatted_results = []
        for result in results:
            chunk = self.env['llm.knowledge.chunk'].search([
                ('vector_id', '=', result['id'])
            ], limit=1)

            if chunk:
                formatted_results.append({
                    'content': chunk.content,
                    'source': chunk.resource_id.name,
                    'similarity_score': result.get('score', 0),
                    'metadata': result.get('metadata', {})
                })

        return {
            'query': query,
            'results_count': len(formatted_results),
            'results': formatted_results
        }
```

## API Reference

### Core Store Methods

```python
# Collection management
def create_collection(self, name, dimension, metric='cosine'):
    """Create new vector collection"""

def delete_collection(self, name):
    """Delete vector collection"""

def list_collections(self):
    """List all collections in store"""

# Vector operations
def insert_vectors(self, collection, vectors, metadata=None, ids=None):
    """Insert vectors into collection"""

def search_vectors(self, collection, query_vector, limit=10, filter=None):
    """Search similar vectors"""

def update_vectors(self, collection, ids, vectors=None, metadata=None):
    """Update existing vectors"""

def delete_vectors(self, collection, ids=None, filter=None):
    """Delete vectors from collection"""

# Utility methods
def get_collection_info(self, collection):
    """Get collection statistics and information"""

def optimize_collection(self, collection):
    """Optimize collection indices and performance"""
```

### Collection Model Methods

```python
# Collection operations
def create_collection(self):
    """Create collection in vector store"""

def drop_collection(self):
    """Delete collection and all vectors"""

# Vector management
def add_vectors(self, vectors, metadata=None, ids=None):
    """Add vectors to this collection"""

def search(self, query_vector, limit=10, filter_metadata=None):
    """Search vectors in this collection"""

def get_vector_count(self):
    """Get total number of vectors in collection"""

def get_all_vectors(self, include_embeddings=True):
    """Get all vectors with optional embedding data"""
```

## Configuration Examples

### Setting Up ChromaDB Store

```python
# Create ChromaDB store
chroma_store = env['llm.store'].create({
    'name': 'Main ChromaDB Store',
    'service': 'chroma',
    'api_base': 'http://localhost:8000',
    'description': 'Primary vector store for knowledge base'
})

# Create collection
knowledge_collection = env['llm.store.collection'].create({
    'name': 'knowledge_base',
    'store_id': chroma_store.id,
    'dimension': 1536,  # OpenAI embedding dimension
    'distance_metric': 'cosine'
})

knowledge_collection.create_collection()
```

### Setting Up pgvector Store

```python
# Create pgvector store (uses existing PostgreSQL)
pgvector_store = env['llm.store'].create({
    'name': 'PostgreSQL Vector Store',
    'service': 'pgvector',
    'description': 'Native PostgreSQL vector storage'
})

# Create collection with custom settings
docs_collection = env['llm.store.collection'].create({
    'name': 'documents',
    'store_id': pgvector_store.id,
    'dimension': 768,  # Smaller dimension for faster queries
    'distance_metric': 'cosine'
})

docs_collection.create_collection()
```

## Performance Optimizations

### Index Management

```python
def optimize_collection_indices(self):
    """Optimize vector store indices for better performance"""

    if self.service == 'pgvector':
        # Optimize pgvector indices
        self._optimize_pgvector_indices()
    elif self.service == 'qdrant':
        # Optimize Qdrant indices
        self._optimize_qdrant_indices()
    elif self.service == 'chroma':
        # ChromaDB auto-optimization
        pass

def _optimize_pgvector_indices(self):
    """Optimize PostgreSQL indices for vector operations"""
    collections = self.env['llm.store.collection'].search([
        ('store_id', '=', self.id)
    ])

    for collection in collections:
        table_name = f"vectors_{collection.name}"

        # Analyze table for statistics
        self.env.cr.execute(f"ANALYZE {table_name};")

        # Update index parameters based on data size
        self.env.cr.execute(f"""
            SELECT COUNT(*) FROM {table_name};
        """)
        row_count = self.env.cr.fetchone()[0]

        if row_count > 10000:
            # Use IVFFlat with more lists for larger datasets
            lists = min(row_count // 1000, 1000)
            self.env.cr.execute(f"""
                DROP INDEX IF EXISTS {table_name}_embedding_idx;
                CREATE INDEX {table_name}_embedding_idx
                ON {table_name} USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = {lists});
            """)
```

### Batch Operations

```python
def insert_vectors_batch(self, collection, vectors, metadata=None, ids=None, batch_size=1000):
    """Insert vectors in optimized batches"""

    total_vectors = len(vectors)
    results = []

    for i in range(0, total_vectors, batch_size):
        batch_end = min(i + batch_size, total_vectors)

        batch_vectors = vectors[i:batch_end]
        batch_metadata = metadata[i:batch_end] if metadata else None
        batch_ids = ids[i:batch_end] if ids else None

        # Insert batch
        batch_result = self._dispatch('insert_vectors',
                                    collection=collection,
                                    vectors=batch_vectors,
                                    metadata=batch_metadata,
                                    ids=batch_ids)

        results.append(batch_result)

        # Progress tracking
        if hasattr(self, '_notify_progress'):
            progress = (batch_end / total_vectors) * 100
            self._notify_progress(f"Inserted {batch_end}/{total_vectors} vectors ({progress:.1f}%)")

    return results
```

## Technical Specifications

### Module Information

- **Name**: LLM Vector Store Base
- **Version**: 18.0.1.0.0
- **Category**: Technical
- **License**: LGPL-3
- **Dependencies**: `llm`, `mail`
- **Author**: Apexive Solutions LLC

### Key Models

- **`llm.store`**: Base vector store configuration
- **`llm.store.collection`**: Vector collection management
- **`llm.store.usage.log`**: Usage tracking and analytics

### Supported Vector Stores

| Provider | Module         | Description                    | Best For                            |
| -------- | -------------- | ------------------------------ | ----------------------------------- |
| ChromaDB | `llm_chroma`   | HTTP-based vector database     | Development and small deployments   |
| pgvector | `llm_pgvector` | PostgreSQL extension           | Production with existing PostgreSQL |
| Qdrant   | `llm_qdrant`   | High-performance vector engine | Large-scale production deployments  |

### Performance Characteristics

| Operation        | ChromaDB | pgvector  | Qdrant    |
| ---------------- | -------- | --------- | --------- |
| Insert Speed     | Good     | Excellent | Excellent |
| Search Speed     | Good     | Very Good | Excellent |
| Scalability      | Limited  | Good      | Excellent |
| Memory Usage     | Moderate | Low       | Moderate  |
| Setup Complexity | Low      | Medium    | Medium    |

## Related Modules

- **`llm`**: Base infrastructure and provider framework
- **`llm_knowledge`**: Knowledge base and RAG integration
- **`llm_chroma`**: ChromaDB vector store implementation
- **`llm_pgvector`**: PostgreSQL pgvector implementation
- **`llm_qdrant`**: Qdrant vector store implementation
- **`llm_tool_knowledge`**: Knowledge search tool integration

## Support & Resources

- **Documentation**: [GitHub Repository](https://github.com/apexive/odoo-llm)
- **Architecture Guide**: [OVERVIEW.md](../OVERVIEW.md)
- **Vector Store Examples**: [Vector Store Guide](examples/)
- **Community**: [GitHub Discussions](https://github.com/apexive/odoo-llm/discussions)

## License

This module is licensed under [LGPL-3](https://www.gnu.org/licenses/lgpl-3.0.html).

---

_© 2025 Apexive Solutions LLC. All rights reserved._
