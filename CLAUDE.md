# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Odoo LLM Integration - A suite of Odoo 18.0 modules for integrating Large Language Models with Odoo ERP. Provides AI-powered chat, knowledge management (RAG), tool execution, and content generation.

## Development Commands

### Code Quality

```bash
# Format and lint Python
ruff format . && ruff check . --fix --unsafe-fixes

# Run pre-commit hooks (includes ESLint, Prettier, Ruff)
pre-commit run --all-files
```

### Testing

```bash
# Run tests for specific module(s)
./run_tests.sh llm_replicate

# Run multiple modules
./run_tests.sh "llm_replicate,llm_comfyui"

# With custom database and port
./run_tests.sh llm_replicate my_test_db 8072

# Direct odoo-bin command for single module
odoo-bin --test-enable --stop-after-init --test-tags=llm -d test_db -u llm
```

## Module Architecture

### Core Dependency Chain

```
llm (base) → llm_thread (chat) → llm_tool (actions) → llm_assistant (AI assistants)
         ↘ llm_store (vector abstraction) → llm_knowledge (RAG) → llm_pgvector/chroma/qdrant
         ↘ llm_generate (content generation) → llm_generate_job (async queue)
```

### Provider Modules

All inherit from `llm.provider` and implement provider-specific API calls:

- **Text/Chat**: `llm_openai`, `llm_ollama`, `llm_mistral`
- **Image**: `llm_replicate`, `llm_fal_ai`, `llm_comfyui`, `llm_comfy_icu`

## Odoo 18.0 Key Patterns

### View Syntax (XML)

```xml
<!-- Use <list> not <tree> -->
<list string="Records">...</list>

<!-- Use direct attributes, not attrs -->
<field name="x" invisible="not active"/>

<!-- Use invisible, not states for buttons -->
<button invisible="state != 'draft'"/>
```

### Frontend Architecture

**Odoo 18 replaced the frontend model system completely:**

```javascript
// ❌ OLD (doesn't exist in 18.0)
import { registerModel, registerPatch } from "@mail/model/model_core";

// ✅ NEW - ES6 classes extending Record
import { Record } from "@mail/core/common/record";
import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";

// Patch existing components
patch(SomeComponent.prototype, {
  setup() {
    super.setup();
    // ...
  },
});
```

### Mail Store Integration

```javascript
// Thread access
mailStore.Thread.get({ model: "llm.thread", id: threadId });

// Message insertion (must also add to thread.messages for UI)
mailStore.insert({ "mail.message": [messageData] }, { html: true });
if (!thread.messages.some((m) => m.id === message.id)) {
  thread.messages.push(message);
}
```

### Backend Message Serialization

```python
from odoo.addons.mail.tools.discuss import Store

def to_store_format(self, message):
    store = Store()
    message._to_store(store)
    return store.get_result()['mail.message'][0]
```

### Removed APIs

- `name_get()` → use `_compute_display_name()` / `display_name` field
- `message_format()` → use `_to_store()` with Store system
- `from odoo import registry` → use `from odoo.modules.registry import Registry`

## LLM Message Flow

1. User sends message → `message_post()` with `llm_role="user"` → saved to DB
2. `generate_messages()` called → `get_llm_messages()` retrieves history
3. Full history passed to LLM provider → streaming response via EventSource
4. Assistant messages processed through `_process_llm_body()` (markdown→HTML)
5. Tool messages use `body_json` field, no HTML processing

## Odoo App Store HTML Guidelines

When editing `static/description/index.html` files:

- Use HTML fragments only (no DOCTYPE, html, head, body)
- No rgba() colors - hex only
- No CSS transitions, transforms, animations, or linear-gradients
- No inline JavaScript
- Use Bootstrap 5 grid (container, row, col-\*)
- Use inline styles for colors/typography

See [ODOO_APP_STORE_HTML_GUIDE.md](./ODOO_APP_STORE_HTML_GUIDE.md) for details.

## Coding Principles

### DRY (Don't Repeat Yourself)

- Extract shared logic into base classes or mixins (e.g., `llm.provider` base for all providers)
- Use `_dispatch()` pattern for extensible behavior instead of duplicating logic
- Common UI components go in base modules, extended via `patch()` in feature modules
- Shared utilities belong in `llm` base module, not duplicated across provider modules

### Odoo Best Practices

- **Inherit, don't copy**: Use `_inherit` to extend models, don't duplicate code
- **Use computed fields**: Prefer `@api.depends` over manual updates
- **Recordsets over IDs**: Pass recordsets between methods, not raw IDs
- **Context for options**: Use `self.with_context()` for optional behavior, not extra parameters
- **SQL only when necessary**: Use ORM unless performance requires raw SQL (then add `_flush()`)
- **Security by design**: Define proper access rules, use `sudo()` sparingly and explicitly
- **Transactional safety**: Use `cr.savepoint()` for operations that might fail partially

### Provider-Agnostic Code

Keep core logic independent of specific LLM providers:

```python
# ✅ Good - provider-agnostic interface
class LlmThread(models.Model):
    def generate_messages(self):
        return self.model_id.provider_id.chat(messages)  # Provider handles specifics

# ❌ Bad - provider-specific code in core
class LlmThread(models.Model):
    def generate_messages(self):
        if self.provider_id.provider == 'openai':
            client = OpenAI(api_key=...)  # Don't do this in core!
```

- All provider-specific logic lives in provider modules (`llm_openai`, `llm_ollama`, etc.)
- Core modules define interfaces via abstract methods or dispatch hooks
- Use `_dispatch(event_name, **kwargs)` for provider-specific transformations
- External API clients are instantiated only in provider modules

### Extension Patterns

```python
# Base module defines hook
class LlmProvider(models.Model):
    def chat(self, messages, **kwargs):
        messages = self._dispatch("normalize_messages", messages=messages)
        return self._chat(messages, **kwargs)  # Abstract, implemented by providers

# Provider module implements
class LlmProviderOpenAI(models.Model):
    _inherit = "llm.provider"

    def _chat(self, messages, **kwargs):
        # OpenAI-specific implementation
```

## External Dependencies by Module

| Module                | Python Dependencies                   |
| --------------------- | ------------------------------------- |
| `llm_knowledge`       | requests, markdownify, PyMuPDF, numpy |
| `llm_pgvector`        | pgvector, numpy                       |
| `llm_chroma`          | chromadb-client, numpy                |
| `llm_qdrant`          | qdrant-client                         |
| `llm_knowledge_llama` | llama_index, nltk                     |
| `llm_openai`          | openai                                |
| `llm_ollama`          | ollama                                |
| `llm_mistral`         | mistralai                             |

## Code Style

- Python: Ruff with Odoo-specific isort sections (odoo → odoo.addons → first-party)
- JavaScript: ESLint with strict rules (no-shadow, valid-jsdoc, sort-imports)
- Max complexity: Python 16, JavaScript 15
