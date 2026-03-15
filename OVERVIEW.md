# Architecture Overview - Odoo LLM Integration

**Version:** Odoo 18.0
**Last Updated:** 2025-10-24
**Status:** Current and accurate for 18.0 migration

This document provides a comprehensive technical overview of the Odoo LLM Integration architecture, covering the consolidated module structure, core concepts, and development patterns.

## Architecture Overview

The Odoo LLM Integration provides a modular framework for integrating Large Language Models into Odoo. The architecture follows a consolidated design with clear separation of concerns, enabling seamless interaction with various AI providers while building sophisticated AI-powered applications.

## Core Module Architecture

The system is built around five core modules that form the foundation for all LLM operations:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   llm (Base)    │    │ llm_assistant   │    │  llm_generate   │
│   Foundation    │◄───┤   Intelligence  │◄───┤   Generation    │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         ▲                       ▲                       ▲
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐              │
│   llm_tool      │    │   llm_store     │              │
│   Actions       │    │   Storage       │              │
│                 │    │                 │              │
└─────────────────┘    └─────────────────┘              │
         ▲                       ▲                       │
         │                       │                       │
         └───────────────────────┴───────────────────────┘
```

### Core Module Responsibilities

1. **`llm`** - Foundation infrastructure and provider abstraction
2. **`llm_assistant`** - Intelligence layer with prompt management
3. **`llm_generate`** - Unified content generation API
4. **`llm_tool`** - Function calling and Odoo integration
5. **`llm_store`** - Vector storage and similarity search

## Enhanced Mail Message System

### Message Extensions

The base `llm` module extends Odoo's core messaging system with AI-specific capabilities:

```python
# Extended mail.message fields
llm_role = fields.Selection([
    ('user', 'User'),
    ('assistant', 'Assistant'),
    ('tool', 'Tool'),
    ('system', 'System')
], compute='_compute_llm_role', store=True, index=True)

body_json = fields.Json()  # Structured data for tool messages
```

### Message Subtypes

Integrated message subtypes for AI interactions:

- **`llm.mt_user`**: User messages in AI conversations
- **`llm.mt_assistant`**: AI-generated responses
- **`llm.mt_tool`**: Tool execution results and data
- **`llm.mt_system`**: System prompts and configuration messages

### Performance Optimization

The **`llm_role` field** provides **10x faster** message queries by:

- Eliminating expensive subtype lookups with indexed field access
- Enabling efficient conversation history processing
- Simplifying frontend filtering and display logic
- Optimizing database operations for large datasets

## Core Models & Concepts

### 1. LLM.Thread (`llm_thread/models/llm_thread.py`)

**Purpose**: Central conversation management and data bridge

```python
class LLMThread(models.Model):
    _name = "llm.thread"
    _description = "LLM Chat Thread"
    _inherit = ["mail.thread"]
```

**Core Function**: Serves as the primary link between Odoo business data and AI conversations:

- **Storage Backend**: Persistent storage for all LLM conversations
- **Data Bridge**: Links any Odoo record to AI conversation threads
- **Conversation Context**: Maintains state, configuration, and history
- **Multi-Threading**: Multiple concurrent conversations per business record

**Key Relationships**:

```
Odoo Record (sale.order, project.task, etc.)
    ↓ (1:many relationship)
LLM Thread(s) - Multiple AI conversations per record
    ↓ (inherits from mail.thread)
Mail Messages - Conversation history with AI enhancements
```

**PostgreSQL Advisory Locking**:

- Prevents concurrent generation conflicts
- Ensures message consistency during streaming
- Database-level coordination for multi-user scenarios

### 2. LLM.Assistant (`llm_assistant/models/llm_assistant.py`)

**Purpose**: Intelligent configuration orchestrator

```python
class LLMAssistant(models.Model):
    _name = "llm.assistant"
    _description = "LLM Assistant"
    _inherit = ["mail.thread"]
```

**Core Function**: Provides the intelligence layer that configures HOW to connect Odoo data to AI models:

**Configuration Domains**:

- **Model Selection**: AI provider and model specification
- **Instruction Templates**: System prompts and conversation templates
- **Data Mapping**: Odoo record transformation to LLM inputs
- **Tool Orchestration**: Available tools and usage patterns
- **Context Management**: History trimming and optimization
- **Generation Parameters**: Content generation configuration

**Consolidated Prompt Management**:
The assistant module now includes integrated prompt template functionality (previously `llm_prompt`):

```python
# Integrated prompt fields
prompt_id = fields.Many2one('llm.prompt')
default_values = fields.Json()  # Default template arguments
```

**Assistant Types**:

1. **Chat Assistants**: Conversational AI with specific personas
2. **Generation Assistants**: Content creation workflows
3. **Analysis Assistants**: Data analysis and insights
4. **Training Assistants**: Model fine-tuning workflows

### 3. LLM.Provider (`llm/models/llm_provider.py`)

**Purpose**: AI service provider abstraction

```python
class LLMProvider(models.Model):
    _name = "llm.provider"
    _inherit = ["mail.thread"]
    _description = "LLM Provider"
```

**Provider Integration Pattern**:

```python
def _dispatch(self, method, *args, **kwargs):
    """Dynamic method dispatch to service implementations"""
    service_method = f"{self.service}_{method}"
    return getattr(self, service_method)(*args, **kwargs)
```

**Supported Providers**:

- **OpenAI** (`llm_openai`): GPT models, DALL-E, embeddings
- **Anthropic** (`llm_anthropic`): Claude models with tool calling
- **Ollama** (`llm_ollama`): Local model deployment
- **Mistral** (`llm_mistral`): Mistral AI models
- **LiteLLM** (`llm_litellm`): Multi-provider proxy
- **Replicate** (`llm_replicate`): Model marketplace access
- **FAL.ai** (`llm_fal_ai`): Fast inference API

### 4. LLM.Tool (`llm_tool/models/llm_tool.py`)

**Purpose**: Function calling and Odoo integration

```python
class LLMTool(models.Model):
    _name = "llm.tool"
    _description = "LLM Tool"
    _inherit = ["mail.thread"]
```

**Enhanced Tool System**:

- **Structured Data Storage**: Tool results in `body_json` format
- **MCP Integration**: Model Context Protocol compatibility
- **Security Framework**: User consent and permission system
- **Error Handling**: Comprehensive error propagation and logging

**Tool Message Format**:

```python
# New structured format
thread.message_post(
    body_json={
        "tool_call_id": "call_123",
        "function": "search_records",
        "arguments": {"model": "sale.order", "domain": [...]},
        "result": {"records": [...], "count": 5}
    },
    llm_role="tool"
)
```

### 5. LLM.Store (`llm_store/models/llm_store.py`)

**Purpose**: Vector storage abstraction

```python
class LLMStore(models.Model):
    _name = "llm.store"
    _inherit = ["mail.thread"]
    _description = "LLM Vector Store"
```

**Vector Store Implementations**:

- **ChromaDB** (`llm_chroma`): HTTP client integration
- **pgvector** (`llm_pgvector`): PostgreSQL extension
- **Qdrant** (`llm_qdrant`): Qdrant vector database

**RAG Integration**:

```python
# Vector similarity search
results = store.search_vectors(
    collection='knowledge_base',
    query_vector=embedding,
    limit=5,
    filter_metadata={"domain": "sales"}
)
```

## Unified Generation System

### Generation API

The `llm_generate` module provides a unified interface for all content generation:

```python
# Unified generation method
response = thread.generate_response(
    user_input="Create a sales report",
    generation_type="text",  # or "image", "audio", etc.
    use_queue=True  # Optional background processing
)
```

### Dynamic Form Generation

Automatic form generation based on model schemas:

```python
def get_input_schema(self):
    """Generate form schema for model inputs"""
    # Priority order:
    # 1. Assistant's prompt schema
    # 2. Thread's direct prompt schema
    # 3. Model's default schema
```

### Race Condition Fixes

Comprehensive fixes for async loading issues:

- **Loading State Management**: Proper async handling in UI components
- **Schema Synchronization**: Automatic prompt argument detection
- **Form Stability**: Prevention of empty forms during loading
- **Context Handling**: Improved state management during updates

## Knowledge Management System

### Consolidated llm_knowledge Module

The `llm_knowledge` module consolidates functionality from the former `llm_resource` module:

**Consolidated Features**:

- **Resource Management**: Document processing and storage (`llm.resource`)
- **RAG Capabilities**: Retrieval-Augmented Generation
- **Vector Integration**: Embedding and similarity search
- **Processing Pipeline**: Retrieve → Parse → Chunk → Embed → Index

**Processing States**:

```
draft → retrieved → parsed → chunked → ready
```

**API Compatibility**: All existing methods preserved:

```python
# Complete processing pipeline
resource.process_resource()  # Full pipeline
resource.retrieve()          # Get content from source
resource.parse()            # Convert to markdown
resource.chunk()            # Split into segments
resource.embed()            # Generate embeddings
```

## Message System Architecture

### Enhanced Message Creation

```python
# Role-based message posting
def message_post(self, body=None, llm_role=None, body_json=None, **kwargs):
    """Enhanced message posting with AI-specific fields"""

    # Automatic role computation from subtype
    if not llm_role and message_type:
        llm_role = self._compute_role_from_subtype(message_type)

    # Structured data handling
    if body_json:
        kwargs['body_json'] = body_json

    return super().message_post(body=body, **kwargs)
```

### Streaming Message Updates

Real-time message creation during AI generation:

```python
def message_post_from_stream(self, stream, llm_role, **kwargs):
    """Create and update message from streaming response"""
    # Create placeholder message
    message = self.message_post(body="", llm_role=llm_role, **kwargs)

    # Update content as stream progresses
    for chunk in stream:
        message.body += chunk
        # Real-time UI updates via bus notifications
```

## Provider Integration Patterns

### Service Registration

```python
@api.model
def _get_available_services(self):
    return super()._get_available_services() + [
        ('openai', 'OpenAI'),
        ('anthropic', 'Anthropic'),
        ('ollama', 'Ollama'),
        # Additional providers...
    ]
```

### Method Implementation Pattern

```python
def openai_chat(self, messages, model=None, stream=False, **kwargs):
    """OpenAI-specific chat implementation"""

def anthropic_chat(self, messages, model=None, stream=False, **kwargs):
    """Anthropic-specific chat implementation"""
```

## Model Context Protocol (MCP) Integration

### MCP Server Configuration

```python
class LLMMCPServer(models.Model):
    _name = "llm.mcp.server"
    _description = "MCP Server Configuration"

    name = fields.Char(required=True)
    command = fields.Char(required=True)  # Server start command
    args = fields.Text()                   # Command arguments
    env_vars = fields.Json()              # Environment variables
```

### Tool Exposure via MCP

```python
def get_tool_definition(self):
    """Returns MCP-compatible tool definition"""
    return {
        "name": self.name,
        "description": self.description,
        "inputSchema": json.loads(self.input_schema or '{}')
    }
```

## Frontend Architecture

### Odoo 18.0 Frontend Changes

**Major architectural shift from Odoo 16.0:**

Odoo 18.0 completely replaced the frontend model system with a new Record-based architecture:

**Removed in 18.0:**

- `registerModel()` - Model registration pattern
- `registerPatch()` - Model patching pattern
- Frontend model definition system

**New in 18.0:**

- ES6 classes extending `Record` from `@mail/core/common/record`
- OWL's `patch()` utility for component extensions
- Built-in reactivity via `@odoo/owl`
- Centralized record storage in `static records`
- Type-safe JSDoc/TypeScript support

**Example migration:**

```javascript
// ❌ Odoo 16.0 pattern (REMOVED)
import { registerModel } from '@mail/model/model_core';
registerModel({
    name: 'Thread',
    fields: { id: attr(), name: attr() }
});

// ✅ Odoo 18.0 pattern (USE THIS)
import { Record } from "@mail/core/common/record";
import { patch } from "@web/core/utils/patch";

export class Thread extends Record {
    static id = AND("model", "id");
    static records = {};
    id; name;
}

patch(Thread.prototype, {
    customMethod() { ... }
});
```

### JavaScript Component Structure

**Core Components**:

- **LLMChatContainer**: Main chat interface controller
- **LLMChatComposer**: Message input and generation forms
- **LLMChatThreadHeader**: Provider/model/assistant selection
- **LLMMediaForm**: Dynamic form generation with schema handling
- **LLMRelatedRecord**: Link chat threads to any Odoo record
- **LLMRecordPickerDialog**: 2-step wizard for record selection

### Real-time Features

- **Streaming Generation**: Live message updates during AI response
- **Tool Execution**: Visual feedback for function calls
- **Context Switching**: Dynamic provider/model/assistant changes
- **Form Generation**: Automatic UI generation from model schemas
- **Related Records**: Link threads to business objects with instant UI updates

## Security & Access Control

### Role-Based Security

**User Groups**:

- **LLM User** (`llm.group_llm_user`): Basic access to AI features
- **LLM Manager** (`llm.group_llm_manager`): Full administrative access

### Tool Security Framework

```python
# Tool consent system
requires_user_consent = fields.Boolean(default=False)
destructive_hint = fields.Boolean(default=False)
read_only_hint = fields.Boolean(default=True)
```

### Record Rules

- Company-based access control for providers
- User-specific thread access restrictions
- Administrative override capabilities

## Performance Optimizations

### Database Improvements

1. **Indexed Role Field**: 10x faster message queries
2. **Reduced Subtype Lookups**: Direct field access instead of joins
3. **PostgreSQL Locking**: Concurrent operation safety
4. **Optimized Vector Queries**: Efficient similarity search

### Frontend Optimizations

1. **Loading State Management**: Prevents UI flashing during async operations
2. **Schema Caching**: Reduced API calls for form generation
3. **Streaming Updates**: Real-time UI updates without full refreshes
4. **Component Reuse**: Efficient component lifecycle management

## Development Patterns

### Adding New Providers

1. **Create Provider Module**: Inherit from `llm.provider`
2. **Implement Service Methods**: Follow naming convention `{service}_{method}`
3. **Register Service**: Add to `_get_available_services()`
4. **Add Configuration**: Provider-specific settings and UI

### Creating Custom Tools

1. **Inherit Tool Model**: Extend `llm.tool`
2. **Implement Execute Method**: `{implementation}_execute()`
3. **Define Schema**: Method signature or JSON schema
4. **Register Implementation**: Add to available implementations

### Extending Message Handling

1. **Override Message Post**: Custom `message_post()` in thread model
2. **Handle Custom Roles**: Process custom `llm_role` values
3. **Process Structured Data**: Handle `body_json` content
4. **Implement Email Patterns**: Custom `email_from` logic

## Migration & Compatibility

### Module Consolidations

**Completed Consolidations** (pre-18.0 migration):

These consolidations were completed in the 16.0 version before the 18.0 migration began:

- `llm_resource` → `llm_knowledge` (resource management + RAG)
- `llm_prompt` → `llm_assistant` (prompt templates + assistants)
- `llm_mail_message_subtypes` → `llm` (message subtypes)

**Migration Scripts**: Automatic migration preserves all data:

- Message subtype conversion
- Tool data format migration
- Module dependency updates
- Configuration preservation

### Odoo 18.0 Migration

**All 26 modules successfully migrated** with the following changes:

- Views: `<tree>` → `<list>`, `attrs` → direct attributes
- Models: `name_get()` → `searchRead()` with `display_name`
- Frontend: `registerModel()` → ES6 classes extending `Record`
- Mail system: Migrated to new mail.store architecture
- UI components: Enhanced reactivity and proper OWL patterns

### Backward Compatibility

- **API Compatibility**: All existing methods continue to work
- **Data Preservation**: Zero data loss during consolidations
- **Configuration Migration**: Settings automatically transferred
- **Progressive Enhancement**: New features don't break existing workflows

This architecture provides a robust, scalable foundation for building sophisticated AI-powered applications within Odoo, with clear patterns for extension and a strong emphasis on performance, security, and maintainability.
