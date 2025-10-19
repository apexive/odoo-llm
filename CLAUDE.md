# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This repository provides a comprehensive framework for integrating Large Language Models (LLMs) into Odoo. It enables seamless interaction with various AI providers (OpenAI, Anthropic, Ollama, Mistral, Replicate, FAL.ai, LiteLLM) for chat completions, embeddings, RAG (Retrieval-Augmented Generation), and content generation.

**Key Context**: This is a backported version on branch `17.0-backport` from the main branch `18.0`. The backport.md file tracks migration status.

## Development Commands

### Code Quality & Linting

```bash
# Run pre-commit hooks (includes ruff, prettier, eslint)
pre-commit run --all-files

# Format Python code with ruff
ruff format .

# Lint and auto-fix Python code
ruff check --fix .

# Run ESLint on JavaScript files
eslint --color --fix **/*.js
```

### Testing

**Note**: Limited test coverage exists (4 test files). Tests are located in module-specific `tests/` directories.

```bash
# Run tests for a specific module (from Odoo root)
odoo-bin -c odoo.conf -d <database> -i <module_name> --test-enable --stop-after-init

# Example: Test llm_assistant module
odoo-bin -c odoo.conf -d test_db -i llm_assistant --test-enable --stop-after-init
```

### Module Installation & Development

```bash
# Install Python dependencies
pip install -r requirements.txt

# Restart Odoo after code changes (from Odoo directory)
# Method depends on your Odoo setup - use supervisorctl, systemctl, or direct odoo-bin

# Update module after changes (from Odoo shell or via UI)
# Via command line:
odoo-bin -c odoo.conf -d <database> -u <module_name>
```

## Architecture

### Core Module Structure

The architecture centers around **five core modules**:

1. **`llm`** (Foundation) - Base infrastructure, provider abstraction, models, enhanced messaging system
2. **`llm_assistant`** (Intelligence) - AI assistants with integrated prompt templates
3. **`llm_generate`** (Generation) - Unified content generation API (text, images, etc.)
4. **`llm_tool`** (Actions) - Tool framework for LLM-Odoo interactions and function calling
5. **`llm_store`** (Storage) - Vector store abstraction for embeddings and similarity search

**Supporting Modules**:
- **`llm_thread`** - Chat thread management with PostgreSQL advisory locking
- **Provider modules** - `llm_openai`, `llm_anthropic`, `llm_ollama`, `llm_mistral`, `llm_replicate`, `llm_fal_ai`, `llm_litellm`
- **Knowledge/RAG** - `llm_knowledge` (consolidated from `llm_resource`), `llm_knowledge_automation`, `llm_tool_knowledge`
- **Vector stores** - `llm_chroma`, `llm_pgvector`, `llm_qdrant`
- **Specialized** - `llm_mcp_server`, `llm_training`, `llm_generate_job`, `llm_document_page`, `llm_letta`

### Key Design Patterns

#### Provider Dispatch Pattern

Providers use dynamic method dispatch to route calls to service-specific implementations:

```python
# In llm.provider model (llm/models/llm_provider.py)
def _dispatch(self, method, *args, **kwargs):
    """Dispatch to service-specific implementation"""
    service_method = f"{self.service}_{method}"  # e.g., "openai_chat"
    return getattr(self, service_method)(*args, **kwargs)

# Provider modules implement: {service}_{method}
# Example in llm_openai: openai_chat(), openai_embedding(), openai_get_client()
```

#### Enhanced Mail Message System

The base `llm` module extends `mail.message` with AI-specific capabilities:

```python
# llm/models/mail_message.py
llm_role = fields.Selection([
    ('user', 'User'),
    ('assistant', 'Assistant'),
    ('tool', 'Tool'),
    ('system', 'System')
], compute='_compute_llm_role', store=True, index=True)  # 10x faster queries

body_json = fields.Json()  # Structured data for tool messages
```

**Performance**: The indexed `llm_role` field eliminates expensive subtype lookups, providing ~10x performance improvement for message queries.

#### Thread as Data Bridge

`llm.thread` serves as the central link between Odoo business data and AI conversations:
- Inherits from `mail.thread` for message storage
- Links to any Odoo record via standard `res_model`/`res_id` pattern
- Supports multiple concurrent conversations per business record
- PostgreSQL advisory locking prevents concurrent generation conflicts

### Module Consolidation History

Recent architecture improvements consolidated related functionality:
- `llm_resource` → `llm_knowledge` (RAG + resource management)
- `llm_prompt` → `llm_assistant` (prompt templates integrated into assistants)
- `llm_mail_message_subtypes` → `llm` (message subtypes in base module)

Migration scripts ensure backward compatibility and zero data loss.

## File Organization

Each Odoo module follows standard structure:

```
module_name/
├── __manifest__.py          # Module metadata, dependencies, assets
├── __init__.py              # Module initialization
├── models/                  # Python business logic
│   ├── __init__.py
│   └── model_name.py
├── views/                   # XML UI definitions
│   └── model_views.xml
├── security/
│   ├── ir.model.access.csv  # Access control lists
│   └── security.xml         # Security groups and rules
├── data/                    # Data files
├── wizards/                 # Transient models for wizards
├── tests/                   # Unit tests
├── static/
│   ├── src/                 # JavaScript/CSS source
│   │   ├── components/      # OWL components
│   │   ├── services/        # JavaScript services
│   │   └── patches/         # Patches to extend core
│   └── description/         # Module images
└── README.md                # Module documentation
```

## Working with This Codebase

### Adding a New AI Provider

1. Create new module `llm_<provider_name>` depending on `llm`
2. Extend `llm.provider` model and implement service methods:
   ```python
   def _get_available_services(self):
       return super()._get_available_services() + [('provider_name', 'Display Name')]

   def provider_name_chat(self, messages, model=None, stream=False, **kwargs):
       # Implementation

   def provider_name_embedding(self, texts, model=None):
       # Implementation

   def provider_name_get_client(self):
       # Return provider client instance
   ```
3. Add external Python dependencies to `__manifest__.py` and update root `requirements.txt`
4. Register in `_get_available_services()` hook

### Adding New Tools

1. Create tool implementation in `llm_tool` or separate module
2. Extend `llm.tool` model with `{implementation}_execute()` method
3. Define input schema (JSON schema or method signature)
4. Set security flags: `requires_user_consent`, `destructive_hint`, `read_only_hint`

### Extending Message Handling

When adding custom message processing:
- Override `message_post()` to handle custom `llm_role` values
- Use `body_json` field for structured data (e.g., tool results)
- Leverage message subtypes: `llm.mt_user`, `llm.mt_assistant`, `llm.mt_tool`, `llm.mt_system`
- Consider streaming updates via `message_post_from_stream()` pattern

### Frontend Development (OWL Components)

JavaScript assets are loaded via `__manifest__.py`:
```python
'assets': {
    'web.assets_backend': [
        'module_name/static/src/components/component_name/component.js',
        'module_name/static/src/components/component_name/component.xml',
        'module_name/static/src/components/component_name/component.scss',
    ],
}
```

Key frontend patterns:
- **Services** integrate with Odoo's service registry (see `llm_store_service.js`)
- **Patches** extend core mail components (composer, thread, message)
- **Client Actions** define standalone views (see `llm_chat_client_action.js`)

## Branch Strategy

- **Main branch**: `18.0` (latest Odoo version)
- **Current branch**: `17.0-backport` (backported version for Odoo 17.0)
- PRs should typically target the main branch unless explicitly for backports
- Check `backport.md` for module backport status

## Important Notes

### Version Numbers

Module versions follow pattern: `{odoo_version}.{major}.{minor}.{patch}`
- Example: `17.0.1.4.0` = Odoo 17.0, module version 1.4.0

### Module Dependencies

Install high-level modules (e.g., `llm_assistant`) to automatically pull in required core modules via Odoo's dependency system. See README.md "Quick Start Guide" section.

### Security Considerations

- API keys stored in `llm.provider.api_key` field
- User groups: `llm.group_llm_user` (basic), `llm.group_llm_manager` (admin)
- Tool consent system requires user approval for sensitive operations
- Record rules enforce company-based and user-specific access control

### Performance Optimizations

Recent improvements include:
- **10x faster message queries** via indexed `llm_role` field
- **PostgreSQL advisory locking** prevents race conditions
- **Module consolidation** reduces complexity
- **Streaming generation** for real-time UI updates

### Known Limitations (17.0 Backport)

Per backport.md, some modules are marked as untested or uninstallable:
- `llm_letta` - uninstallable
- `llm_replicate` - uninstallable
- `llm_thread`, `llm_assistant`, `llm_generate` - marked as untested

Patches in `llm_thread` may be commented out due to conflicts.

**Important llm_thread fix**: If experiencing white screen issues, ensure the `action` service is properly initialized in `llm_chat_client_action.js:22`. See `LLM_THREAD_V17_FIX.md` for detailed troubleshooting.
