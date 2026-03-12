# Odoo LLM Integration

![Banner](llm/static/description/banner.jpeg)

This repository provides a comprehensive framework for integrating Large Language Models (LLMs) into Odoo. It allows seamless interaction with various AI providers including OpenAI, Anthropic, Ollama, and Replicate, enabling chat completions, text embeddings, and more within your Odoo environment.

## 🏗️ Architecture

```mermaid
graph TD
    subgraph External AI Clients
        CD[Claude Desktop<br>Cursor · Windsurf]
        CC[Claude Code<br>Codex CLI]
    end

    subgraph Odoo AI Chat
        LA[llm_assistant]
        LT[llm_thread]
    end

    CD -->|MCP Protocol| MCP
    CC -->|MCP Protocol| MCP

    LA --> LLM
    LT --> LLM

    MCP[llm_mcp_server<br>MCP Server for Odoo] --> LLM

    LLM[⭐ llm ⭐<br>Provider Abstraction · Model Management<br>Enhanced mail.message · Security Framework]

    LLM --> TOOL[llm_tool<br>Tool Framework + Generic CRUD Tools]
    LLM --> PROV[AI Providers<br>llm_openai · llm_ollama<br>llm_mistral · ...]
    LLM --> INFRA[Infrastructure<br>llm_store · llm_generate]

    TOOL --> PACKS[Domain-Specific Tool Packs<br>llm_tool_account · 18 accounting tools<br>llm_tool_mis_builder · 44 MIS reporting tools<br>llm_tool_knowledge · RAG search tools<br>llm_tool_ocr_mistral · OCR via Mistral vision]

    style LLM fill:#f9f8fc,stroke:#71639e,stroke-width:3px,color:#71639e
    style MCP fill:#fff,stroke:#71639e,stroke-width:2px,color:#71639e
    style TOOL fill:#fff,stroke:#71639e,stroke-width:2px,color:#71639e
    style PACKS fill:#f9f8fc,stroke:#71639e,stroke-width:2px,color:#71639e
    style PROV fill:#fff,stroke:#dee2e6,stroke-width:2px
    style INFRA fill:#fff,stroke:#dee2e6,stroke-width:2px
```

Two ways to use AI with Odoo — both powered by the same tool framework:

- **External AI Clients** (Claude Desktop, Claude Code, Cursor, Codex CLI) connect via `llm_mcp_server` using the Model Context Protocol
- **Odoo AI Chat** (`llm_assistant` + `llm_thread`) provides a built-in chat interface inside Odoo

Both feed into the **`llm` core** module, which provides provider abstraction, model management, and security. Below that:

- **`llm_tool`** — function-calling framework with 6 generic CRUD tools out of the box, plus domain-specific tool packs (accounting, MIS Builder, knowledge, OCR)
- **AI Providers** — `llm_openai`, `llm_ollama`, `llm_mistral`, and more (any OpenAI-compatible API works)
- **Infrastructure** — `llm_store` (vector storage), `llm_generate` (content generation)

## 🚀 Latest Updates (Version 18.0)

### **Major Architecture Improvements**
- **Consolidated Architecture**: Merged `llm_resource` into `llm_knowledge` and `llm_prompt` into `llm_assistant` for streamlined management
- **Performance Optimization**: Added indexed `llm_role` field for 10x faster message queries and improved database performance  
- **Unified Generation API**: New `generate()` method provides consistent content generation across all model types (text, images, etc.)
- **Enhanced Tool System**: Simplified tool execution with structured `body_json` storage and better error handling
- **PostgreSQL Advisory Locking**: Prevents concurrent generation issues with proper database-level locks

### **Developer Experience Enhancements**
- **Cleaner APIs**: Simplified method signatures with `llm_role` parameter instead of complex subtype handling
- **Better Debugging**: Enhanced logging, error messages, and comprehensive test coverage throughout the system
- **Reduced Dependencies**: Eliminated separate modules by consolidating related functionality

### **Odoo 18.0 Migration Status**

**✅ Available in 18.0:**
- Core: llm, llm_thread, llm_tool, llm_assistant
- Text/Chat Providers: llm_openai, llm_ollama, llm_mistral, llm_anthropic
- Image Providers: llm_replicate, llm_fal_ai, llm_comfyui, llm_comfy_icu
- Knowledge System: llm_knowledge, llm_pgvector, llm_chroma, llm_qdrant
- Knowledge Extensions: llm_knowledge_automation, llm_knowledge_llama, llm_knowledge_mistral, llm_tool_knowledge
- Generation: llm_generate, llm_generate_job, llm_training
- Domain Tools: llm_tool_account, llm_tool_mis_builder, llm_tool_ocr_mistral, llm_tool_demo
- Integrations: llm_letta, llm_mcp_server, llm_document_page, llm_store

**⏳ Available in 16.0 branch only:**
- llm_litellm - LiteLLM proxy integration
- llm_mcp - Model Context Protocol (client)

**Migration Highlights:**
- Updated UI components with modern mail.store architecture
- Related Record component for linking threads to any Odoo record
- All views, models, and frontend aligned with Odoo 18.0 standards

## 🚀 Features

- **Multiple LLM Provider Support**: Connect to OpenAI, Anthropic, Ollama, Mistral, Replicate, FAL.ai, ComfyUI, and more.
- **Unified API**: Consistent interface for all LLM operations regardless of the provider.
- **Modern Chat UI**: Responsive interface with real-time streaming, tool execution display, and assistant switching.
- **Thread Management**: Organize and manage AI conversations with context and related record linking.
- **Model Management**: Configure and utilize different models for chat, embeddings, and content generation.
- **Knowledge Base (RAG)**: Store, index, and retrieve documents for Retrieval-Augmented Generation.
- **Vector Store Integrations**: Supports ChromaDB, pgvector, and Qdrant for efficient similarity searches.
- **Advanced Tool Framework**: Allows LLMs to interact with Odoo data, execute actions, and use custom tools via `@llm_tool` decorator.
- **MCP Server**: Connect Claude Desktop, Claude Code, Codex CLI, Cursor, and other MCP clients directly to Odoo.
- **Domain-Specific Tools**: 18 accounting tools (trial balance, tax reports, reconciliation) and 44 MIS Builder tools (KPIs, variance analysis, drilldown).
- **AI Assistants with Prompts**: Build specialized AI assistants with custom instructions, prompt templates, and tool access.
- **Content Generation**: Generate images, text, and other content types using specialized models.
- **Security**: Role-based access control, secure API key management, and permission-based tool access.

## 📦 Core Modules

The architecture centers around five core modules that provide the foundation for all LLM operations:

| Module | Version | Purpose |
|--------|---------|---------|
| **`llm`** | 18.0.1.7.0 | **Foundation** - Base infrastructure, providers, models, and enhanced messaging system |
| **`llm_assistant`** | 18.0.1.5.4 | **Intelligence** - AI assistants with integrated prompt templates and testing |
| **`llm_generate`** | 18.0.2.0.0 | **Generation** - Unified content generation API for text, images, and more |
| **`llm_tool`** | 18.0.4.1.1 | **Actions** - Tool framework for LLM-Odoo interactions and function calling |
| **`llm_store`** | 18.0.1.0.0 | **Storage** - Vector store abstraction for embeddings and similarity search |

## 📦 All Available Modules

| Module | Version | Description |
|--------|---------|-------------|
| **Core Infrastructure** | | |
| `llm` | 18.0.1.7.0 | Base module with providers, models, and enhanced messaging |
| `llm_assistant` | 18.0.1.5.4 | AI assistants with integrated prompt templates |
| `llm_generate` | 18.0.2.0.0 | Unified content generation with dynamic forms |
| `llm_tool` | 18.0.4.1.1 | Tool framework with @llm_tool decorator and auto-registration |
| `llm_store` | 18.0.1.0.0 | Vector store abstraction layer |
| **Chat & Threading** | | |
| `llm_thread` | 18.0.1.4.5 | Chat threads with PostgreSQL locking and related record linking |
| **AI Providers - Text/Chat** | | |
| `llm_openai` | 18.0.1.4.0 | OpenAI (GPT) provider integration with enhanced tool support |
| `llm_anthropic` | 18.0.1.1.0 | Anthropic Claude provider integration |
| `llm_ollama` | 18.0.1.2.0 | Ollama provider for local model deployment |
| `llm_mistral` | 18.0.1.0.3 | Mistral AI provider integration |
| **AI Providers - Image Generation** | | |
| `llm_replicate` | 18.0.1.1.1 | Replicate.com provider integration |
| `llm_fal_ai` | 18.0.2.0.1 | FAL.ai provider with unified generate endpoint |
| `llm_comfyui` | 18.0.1.0.2 | ComfyUI integration for advanced image workflows |
| `llm_comfy_icu` | 18.0.1.0.0 | ComfyICU integration for image generation |
| **Knowledge & RAG** | | |
| `llm_knowledge` | 18.0.1.1.0 | RAG functionality with document management and semantic search |
| `llm_knowledge_automation` | 18.0.1.0.0 | Automation rules for knowledge processing |
| `llm_knowledge_llama` | 18.0.1.0.0 | LlamaIndex integration for advanced knowledge processing |
| `llm_knowledge_mistral` | 18.0.1.0.0 | OCR vision AI using Mistral vision models |
| `llm_tool_knowledge` | 18.0.1.0.1 | Tool for LLMs to query the knowledge base |
| **Vector Stores** | | |
| `llm_chroma` | 18.0.1.0.0 | ChromaDB vector store integration |
| `llm_pgvector` | 18.0.1.0.0 | pgvector (PostgreSQL) vector store integration |
| `llm_qdrant` | 18.0.1.0.0 | Qdrant vector store integration |
| **Domain-Specific Tools** | | |
| `llm_tool_account` | 18.0.1.0.0 | 18 accounting tools: trial balance, tax reports, journal entries, reconciliation, payments, period close |
| `llm_tool_mis_builder` | 18.0.1.0.0 | 44 MIS Builder tools: KPIs, periods, report execution, drilldown, variance analysis |
| `llm_tool_ocr_mistral` | 18.0.1.0.1 | Extract text from images and PDFs using Mistral AI vision models |
| `llm_tool_demo` | 18.0.1.0.0 | Demonstration of @llm_tool decorator usage |
| **Integrations & Specialized Features** | | |
| `llm_mcp_server` | 18.0.1.3.1 | MCP server exposing Odoo tools to Claude Desktop, Claude Code, Codex CLI |
| `llm_letta` | 18.0.1.0.4 | Letta agent-based AI with persistent memory and MCP tools |
| `llm_training` | 18.0.1.0.0 | Fine-tuning dataset and training job management |
| `llm_generate_job` | 18.0.1.0.0 | Job queue management for content generation |
| `llm_document_page` | 18.0.1.0.0 | Integration with document pages and knowledge articles |

## 🛠️ Installation

**Requirements:**
- Odoo 18.0+ (for 16.0 version, see `16.0` branch)
- Python 3.11+
- PostgreSQL 14+ (recommended for pgvector support)

Install these modules by cloning the repository and making them available in your Odoo addons path:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/apexive/odoo-llm
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Make modules available to Odoo:**
   ```bash
   # Option A: Clone directly into addons directory
   cd /path/to/your/odoo/addons/
   git clone https://github.com/apexive/odoo-llm
   
   # Option B: Copy modules to extra-addons
   cp -r /path/to/odoo-llm/* /path/to/your/odoo/extra-addons/
   ```

4. **Restart Odoo and install modules** through the Apps menu

## 🚀 Quick Start Guide

Thanks to Odoo's dependency management, you only need to install the end modules to get started:

### 1. **Complete AI Assistant Setup** (Recommended)
```
Install: llm_assistant + llm_openai (or llm_ollama, llm_mistral)
```
**What you get:**
- ✅ Full chat interface with AI assistants
- ✅ Prompt template management and testing
- ✅ Tool framework for Odoo interactions
- ✅ Content generation capabilities
- ✅ Optimized message handling (10x faster)

**Available providers:** OpenAI, Ollama, Mistral

### 2. **Knowledge Base (RAG) Setup**
```
Install: llm_knowledge + llm_pgvector (or llm_chroma/llm_qdrant)
```
**What you get:**
- ✅ Document embedding and retrieval
- ✅ Vector similarity search
- ✅ RAG-enhanced conversations
- ✅ Automated knowledge processing

### 3. **Advanced Content Generation**
```
Install: llm_generate + llm_fal_ai (for images)
```
**What you get:**
- ✅ Image generation from text prompts
- ✅ Dynamic form generation based on schemas
- ✅ Streaming generation responses
- ✅ Multi-format content support

### 4. **MCP Server + Accounting Tools** (for Claude Desktop / Claude Code)
```
Install: llm_mcp_server + llm_tool_account
```
**What you get:**
- ✅ Connect Claude Desktop, Claude Code, or Codex CLI to Odoo
- ✅ 18 accounting tools: trial balance, tax reports, journal entries, reconciliation
- ✅ Natural language access to all Odoo data via generic CRUD tools
- ✅ User-scoped API keys with full permission enforcement

**Optional add-on:** `llm_tool_mis_builder` for 44 MIS Builder reporting tools

### 5. **Local AI Deployment**
```
Install: llm_ollama + llm_assistant
```
**What you get:**
- ✅ Privacy-focused local AI models
- ✅ No external API dependencies
- ✅ Full feature compatibility
- ✅ Custom model support

## ⚙️ Configuration

After installation:

1. **Set up AI Provider:**
   - Navigate to **LLM → Configuration → Providers**
   - Create a new provider with your API credentials
   - Use "Fetch Models" to automatically import available models

2. **Create AI Assistants:**
   - Go to **LLM → Configuration → Assistants**
   - Configure assistants with specific roles and instructions
   - Assign prompt templates and available tools

3. **Configure Access Rights:**
   - Grant appropriate permissions to users
   - Set up tool consent requirements
   - Configure security policies

4. **Set up Knowledge Base (optional):**
   - Configure vector store connections
   - Create knowledge collections
   - Import and process documents

## 🔄 LLM Tools: Building AI-Driven ERP

This integration enables revolutionary AI-powered business processes:

### **Why This Matters**
- **AI-driven automation** of repetitive tasks with sophisticated tool execution
- **Smart querying & decision-making** with direct access to Odoo data
- **Flexible ecosystem** for custom AI assistants with role-specific configurations
- **Real-time streaming** interactions with enterprise-grade reliability

### **Recent Performance Improvements**
- **10x Performance Boost**: New `llm_role` field eliminates expensive database lookups
- **Simplified Architecture**: Module consolidation reduces complexity and maintenance
- **Enhanced Tool System**: Better error handling and structured data storage
- **PostgreSQL Locking**: Prevents race conditions in concurrent scenarios
- **Unified Generation API**: Consistent interface across all content types

### **Enterprise-Ready Features**
- **PostgreSQL Advisory Locking**: Prevents concurrent generation conflicts
- **Role-Based Security**: Granular access control for AI features
- **Tool Consent System**: User approval for sensitive operations
- **Audit Trail**: Complete tracking of AI interactions and tool usage
- **Migration Support**: Automatic upgrades preserve existing data

## 🤝 Contributing

We're committed to building an open AI layer for Odoo that benefits everyone. Areas where we welcome contributions:

- **Testing & CI/CD**: Unit tests for the consolidated architecture
- **Security Enhancements**: Access control and audit improvements  
- **Provider Integrations**: Support for additional AI services
- **Localization**: Translations and regional customizations
- **Documentation**: Examples, tutorials, and use case guides
- **Performance**: Optimization and scalability improvements

### **How to Contribute**
1. **Issues**: Report bugs or suggest features via GitHub Issues
2. **Discussions**: Join conversations about priorities and approaches
3. **Pull Requests**: Submit code contributions following our guidelines

### **Development Guidelines**
- Follow existing code style and structure
- Write comprehensive tests for new functionality
- Update documentation for changes
- Test with the consolidated architecture
- Include migration scripts for breaking changes

## 🔮 Roadmap

- [x] **Enhanced RAG** capabilities ✅ *Production ready*
- [x] **Function calling support** ✅ *Advanced tool framework*
- [x] **Prompt template management** ✅ *Integrated in assistants*
- [x] **Performance optimization** ✅ *10x improvement achieved*
- [x] **Content generation** ✅ *Unified API implemented*
- [x] **Module consolidation** ✅ *Architecture simplified*
- [x] **Multi-modal content** ✅ *Image + text generation fully working*
- [x] **Odoo 18.0 migration** ✅ *Core modules and integrations migrated*
- [x] **MCP Server** ✅ *Connect Claude Desktop, Claude Code, Codex CLI to Odoo*
- [x] **Domain-specific tools** ✅ *Accounting (18 tools) and MIS Builder (44 tools)*
- [ ] **Advanced workflow automation** 🔄 *Business process AI*
- [ ] **More domain tools** 🔄 *CRM, HR, Manufacturing, Inventory*
- [ ] **Model fine-tuning workflows** 🔄 *Custom model training*

## 📈 Performance & Migration

The latest version includes significant architectural improvements:

- **Backward Compatible**: All existing installations automatically migrate
- **Performance Gains**: Up to 10x faster message queries with optimized database schema
- **Reduced Complexity**: Consolidated modules eliminate maintenance overhead
- **Enhanced Reliability**: PostgreSQL advisory locking prevents concurrent issues
- **Data Preservation**: Zero data loss during module consolidations

For detailed migration information, see [CHANGELOG.md](CHANGELOG.md).

## 📜 License

This project is licensed under LGPL-3 - see the [LICENSE](LICENSE) file for details.

## 🌐 About

Developed by [Apexive](https://apexive.com) - We're passionate about bringing advanced AI capabilities to the Odoo ecosystem.

**Support & Resources:**
- **Documentation**: [GitHub Repository](https://github.com/apexive/odoo-llm)
- **Community Support**: [GitHub Discussions](https://github.com/apexive/odoo-llm/discussions)
- **Bug Reports**: [GitHub Issues](https://github.com/apexive/odoo-llm/issues)
- **Architecture Details**: [OVERVIEW.md](OVERVIEW.md)
- **Change History**: [CHANGELOG.md](CHANGELOG.md)

---

*For questions, support, or collaboration opportunities, please open an issue or discussion in this repository.*
