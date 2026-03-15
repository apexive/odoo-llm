==========================================
Anthropic Provider for Odoo LLM
==========================================

Anthropic Claude integration - Advanced AI with safety and reasoning at its core.

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
              │        ★ llm_anthropic (This Module) ★        │
              │              Anthropic Provider               │
              │  Claude 4.5 │ Claude 4 │ Claude 3.x │ Vision  │
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

**For AI chat with Claude:**

.. code-block:: bash

    odoo-bin -d your_db -i llm_assistant,llm_anthropic

Auto-Installed Dependencies
---------------------------

- ``llm`` (core infrastructure)
- ``llm_tool`` (tool/function calling support)

Why Choose Claude?
------------------

+-------------------+------------------------------------------------+
| Feature           | Claude                                         |
+===================+================================================+
| **Safety**        | 🛡️ Constitutional AI for aligned responses    |
+-------------------+------------------------------------------------+
| **Context**       | 📚 200K+ token context window                  |
+-------------------+------------------------------------------------+
| **Reasoning**     | 🧠 Extended thinking mode available            |
+-------------------+------------------------------------------------+
| **Vision**        | 👁️ Advanced multimodal capabilities            |
+-------------------+------------------------------------------------+
| **Tool Calling**  | 🔧 Native function calling support             |
+-------------------+------------------------------------------------+

Common Setups
-------------

+---------------------------+----------------------------------------------+
| I want to...              | Install                                      |
+===========================+==============================================+
| Chat with Claude          | ``llm_assistant`` + ``llm_anthropic``        |
+---------------------------+----------------------------------------------+
| Claude + document search  | Above + ``llm_knowledge`` + ``llm_pgvector`` |
+---------------------------+----------------------------------------------+
| Claude + external tools   | Above + ``llm_mcp_server``                   |
+---------------------------+----------------------------------------------+

Features
========

- Connect to Anthropic API with proper authentication
- Support for all Claude models (4.5, 4, 3.x series)
- Tool/function calling capabilities
- Extended thinking support (Claude's reasoning mode)
- Streaming responses
- Multimodal (vision) capabilities for supported models
- Automatic model discovery

Supported Models
================

Claude 4.5 Series
-----------------

- **Claude 4.5 Opus** - Highest capability, complex tasks
- **Claude 4.5 Sonnet** - Balanced performance and speed
- **Claude 4.5 Haiku** - Fast, cost-effective

**All support:** Chat, Vision, Tools, Extended Thinking

Claude 4 Series
---------------

- **Claude 4 Opus** - Previous generation flagship
- **Claude 4 Sonnet** - Balanced Claude 4 model

**All support:** Chat, Vision, Tools

Claude 3.x Series
-----------------

- **Claude 3 Opus** - Proven high-capability model
- **Claude 3 Sonnet** - Balanced performance
- **Claude 3 Haiku** - Fast, efficient

**All support:** Chat, Vision, Tools

Configuration
=============

1. Install the module
2. Go to **LLM → Configuration → Providers**
3. Create a new provider and select "Anthropic"
4. Enter your Anthropic API key from console.anthropic.com
5. Click "Fetch Models" to import available models

Extended Thinking
=================

Claude supports extended thinking mode, which allows the model to show its reasoning process:

.. code-block:: python

    # Enable extended thinking in your assistant configuration
    response = provider.chat(
        messages=messages,
        extended_thinking=True,
        thinking_budget=10000  # tokens for reasoning
    )

Key Differences from OpenAI
============================

+------------------+-------------------------------------------+-------------------------------------------+
| Aspect           | OpenAI                                    | Anthropic                                 |
+==================+===========================================+===========================================+
| System message   | In messages array                         | Separate ``system`` parameter             |
+------------------+-------------------------------------------+-------------------------------------------+
| Tool format      | ``{"type": "function", "function": {}}``  | ``{"name", "description", "schema"}``     |
+------------------+-------------------------------------------+-------------------------------------------+
| Response content | Single string                             | Array of content blocks                   |
+------------------+-------------------------------------------+-------------------------------------------+
| Tool results     | ``role: "tool"``                          | ``role: "user"`` + ``type: "tool_use"``   |
+------------------+-------------------------------------------+-------------------------------------------+
| Thinking         | Not available                             | Extended thinking mode                    |
+------------------+-------------------------------------------+-------------------------------------------+

Technical Specifications
========================

- **Version**: 18.0.1.0.0
- **License**: LGPL-3
- **Dependencies**: ``llm``, ``llm_tool``
- **Python Package**: ``anthropic``

Implemented Methods
===================

- ``anthropic_get_client()`` - Initialize Anthropic client
- ``anthropic_chat()`` - Chat with tool calling and streaming support
- ``anthropic_format_tools()`` - Convert tools to Anthropic format
- ``anthropic_format_messages()`` - Format mail.message records
- ``anthropic_models()`` - List available Claude models
- ``anthropic_normalize_prepend_messages()`` - Handle prepend messages

Related Modules
===============

- **``llm``** - Core infrastructure
- **``llm_tool``** - Tool calling support
- **``llm_assistant``** - AI assistants
- **``llm_knowledge``** - RAG with semantic search
- **``llm_openai``** - Alternative: OpenAI
- **``llm_ollama``** - Alternative: local AI
- **``llm_mistral``** - Alternative: Mistral AI

Contributors
============

- Crottolo <bo@fl1.cz> - Odoo 18.0 port with full tool calling and extended thinking support

License
=======

LGPL-3

----

*© 2025 Apexive Solutions LLC*
