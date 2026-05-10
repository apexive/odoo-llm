==========================================
Ollama Provider for Odoo LLM Integration
==========================================

Local AI deployment with Ollama - privacy-focused, no API costs.

**Module Type:** 🔧 Provider (Local/Privacy-Focused)

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
              │          ★ llm_ollama (This Module) ★         │
              │           Ollama Provider (Local AI)          │
              │  🔒 Llama 3 │ Mistral │ CodeLlama │ Phi │ etc │
              └─────────────────────┬─────────────────────────┘
                        ┌───────────┴───────────┐
                        ▼                       ▼
    ┌───────────────────────────┐   ┌───────────────────────────┐
    │           llm             │   │      Ollama Server        │
    │    (Core Base Module)     │   │   (localhost:11434)       │
    └───────────────────────────┘   └───────────────────────────┘

Installation
============

What to Install
---------------

**For local AI chat (no external API):**

.. code-block:: bash

    # 1. Install Ollama on your server first
    curl -fsSL https://ollama.ai/install.sh | sh
    ollama pull llama3

    # 2. Install the Odoo module
    odoo-bin -d your_db -i llm_assistant,llm_ollama

Why Choose Ollama?
------------------

+-------------+----------------------+-------------------+
| Feature     | Ollama               | Cloud Providers   |
+=============+======================+===================+
| **Privacy** | 🔒 Data stays local  | ☁️ Sent to cloud  |
+-------------+----------------------+-------------------+
| **Cost**    | 💰 Free (your hardware) | 💳 Pay per token|
+-------------+----------------------+-------------------+
| **Offline** | ✅ Works offline     | ❌ Requires internet|
+-------------+----------------------+-------------------+

Common Setups
-------------

+---------------------------+----------------------------------------------+
| I want to...              | Install                                      |
+===========================+==============================================+
| Local AI chat             | ``llm_assistant`` + ``llm_ollama``           |
+---------------------------+----------------------------------------------+
| Local AI + RAG            | Above + ``llm_knowledge`` + ``llm_pgvector`` |
+---------------------------+----------------------------------------------+
| Mixed (local + cloud)     | Install both ``llm_ollama`` + ``llm_openai`` |
+---------------------------+----------------------------------------------+

Features
========

- Connect to Ollama with proper configuration
- Support for various open-source models (Llama, Mistral, etc.)
- Text generation capabilities
- Function calling support
- Automatic model discovery
- Local deployment for privacy and control

Configuration
=============

1. Install Ollama on your server
2. Navigate to **LLM > Configuration > Providers**
3. Create provider with URL (default: http://localhost:11434)
4. Click "Fetch Models" to import available models

Technical Specifications
========================

- **Version**: 18.0.1.1.0
- **License**: LGPL-3
- **Dependencies**: ``llm``
- **Python Package**: ``ollama``

Related Modules
===============

- **``llm``** - Core infrastructure
- **``llm_assistant``** - AI assistants
- **``llm_openai``** - Alternative: OpenAI
- **``llm_mistral``** - Alternative: Mistral AI

License
-------

LGPL-3

----

*© 2025 Apexive Solutions LLC*
