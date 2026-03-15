==========================================
OpenAI Provider for Odoo LLM Integration
==========================================

OpenAI API integration providing access to GPT models, embeddings, and DALL-E.

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
              │          ★ llm_openai (This Module) ★         │
              │              OpenAI Provider                  │
              │  GPT-4o │ GPT-4 │ GPT-3.5 │ DALL-E │ Embeddings │
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

**For AI chat with OpenAI:**

.. code-block:: bash

    odoo-bin -d your_db -i llm_assistant,llm_openai

Auto-Installed Dependencies
---------------------------

- ``llm`` (core infrastructure)

Common Setups
-------------

+---------------------------+----------------------------------------------+
| I want to...              | Install                                      |
+===========================+==============================================+
| Chat with GPT-4           | ``llm_assistant`` + ``llm_openai``           |
+---------------------------+----------------------------------------------+
| GPT + document search     | Above + ``llm_knowledge`` + ``llm_pgvector`` |
+---------------------------+----------------------------------------------+
| GPT + external tools      | Above + ``llm_mcp_server``                   |
+---------------------------+----------------------------------------------+

Features
========

- Connect to OpenAI API with proper authentication
- Support for all OpenAI models (GPT-4o, GPT-4, GPT-3.5, etc.)
- Text embeddings support
- Function calling capabilities
- Automatic model discovery
- OpenAI-compatible endpoint support

Configuration
=============

1. Install the module
2. Navigate to **LLM > Configuration > Providers**
3. Create a new provider and select "OpenAI"
4. Enter your OpenAI API key
5. Click "Fetch Models" to import available models

Technical Specifications
========================

- **Version**: 18.0.1.1.3
- **License**: LGPL-3
- **Dependencies**: ``llm``
- **Python Package**: ``openai``

Related Modules
===============

- **``llm``** - Core infrastructure
- **``llm_assistant``** - AI assistants
- **``llm_ollama``** - Alternative: local AI
- **``llm_mistral``** - Alternative: Mistral AI

License
=======

LGPL-3

----

*© 2025 Apexive Solutions LLC*
