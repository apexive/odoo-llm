==========================================
Mistral AI Provider for Odoo LLM
==========================================

Mistral AI integration - European, fast, GDPR-friendly.

**Module Type:** 🔧 Provider

Architecture
============

::

    ┌─────────────────────────────────────────────────────────────────┐
    │                    Used By (Any LLM Module)                     │
    │  ┌─────────────┐  ┌───────────┐  ┌─────────────┐  ┌───────────┐ │
    │  │llm_assistant│  │llm_thread │  │llm_knowledge│  │llm_generate│ │
    │  └──────┬──────┘  └─────┬─────┘  └──────┬──────┘  └─────┬─────┘ │
    └─────────┼───────────────┼───────────────┼───────────────┼───────┘
              └───────────────┴───────┬───────┴───────────────┘
                                      ▼
              ┌───────────────────────────────────────────────┐
              │          ★ llm_mistral (This Module) ★        │
              │              Mistral AI Provider              │
              │  Mistral Large │ Medium │ Small │ Embeddings  │
              └─────────────────────┬─────────────────────────┘
                                    ▼
              ┌───────────────────────────────────────────────┐
              │                    llm                        │
              │              (Core Base Module)               │
              └───────────────────────────────────────────────┘

Installation
============

What to Install
---------------

**For AI chat with Mistral:**

.. code-block:: bash

    odoo-bin -d your_db -i llm_assistant,llm_mistral

Why Choose Mistral?
-------------------

+----------------+-------------------------------+
| Feature        | Mistral                       |
+================+===============================+
| **Location**   | 🇪🇺 European (GDPR friendly) |
+----------------+-------------------------------+
| **Speed**      | ⚡ Very fast inference        |
+----------------+-------------------------------+
| **Cost**       | 💰 Competitive pricing        |
+----------------+-------------------------------+
| **Embeddings** | ✅ High-quality embeddings    |
+----------------+-------------------------------+

Common Setups
-------------

+---------------------------+----------------------------------------------+
| I want to...              | Install                                      |
+===========================+==============================================+
| Chat with Mistral         | ``llm_assistant`` + ``llm_mistral``          |
+---------------------------+----------------------------------------------+
| Mistral + RAG             | Above + ``llm_knowledge`` + ``llm_pgvector`` |
+---------------------------+----------------------------------------------+
| Mistral OCR               | ``llm_knowledge_mistral``                    |
+---------------------------+----------------------------------------------+

Features
========

- Chat completion support
- Streaming responses
- Model management
- API key configuration
- High-quality embeddings

Configuration
=============

1. Install the module
2. Go to **Settings → LLM → Providers**
3. Create a Mistral provider with your API key
4. Fetch available models

Technical Specifications
========================

- **Version**: 18.0.1.0.0
- **License**: LGPL-3
- **Dependencies**: ``llm``
- **Python Package**: ``mistralai``

Related Modules
===============

- **``llm``** - Core infrastructure
- **``llm_assistant``** - AI assistants
- **``llm_knowledge_mistral``** - Mistral OCR for knowledge base
- **``llm_openai``** - Alternative: OpenAI
- **``llm_ollama``** - Alternative: local AI

License
-------

LGPL-3

----

*© 2025 Apexive Solutions LLC*
