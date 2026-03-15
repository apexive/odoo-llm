==============================
LLM Integration Base for Odoo
==============================

The foundational module for integrating Large Language Models into Odoo.

**Module Type:** 📦 Infrastructure (Core Foundation)

Architecture
============

::

                            ┌─────────────────────────────────────────────────────────┐
                            │              Layer 2: Interfaces                        │
                            │  ┌─────────────┐ ┌───────────┐ ┌──────────────────────┐ │
                            │  │llm_assistant│ │llm_thread │ │    llm_mcp_server    │ │
                            │  └──────┬──────┘ └─────┬─────┘ └──────────┬───────────┘ │
                            └─────────┼──────────────┼──────────────────┼─────────────┘
                                      │              │                  │
                                      ▼              ▼                  ▼
    ┌─────────────────────────────────────────────────────────────────────────────────┐
    │                              ★ llm (This Module) ★                              │
    │                              Core Odoo-LLM Base                                 │
    │  ┌─────────────────────────────────────────────────────────────────────────┐   │
    │  │ • Provider Abstraction  • Model Management  • Enhanced mail.message     │   │
    │  └─────────────────────────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────────────────────────┘
                                      ▲              ▲
              ┌───────────────────────┼──────────────┼───────────────────────┐
              │                       │              │                       │
        ┌─────┴─────┐          ┌──────┴─────┐  ┌─────┴──────┐         ┌──────┴─────┐
        │llm_openai │          │ llm_ollama │  │llm_mistral │         │llm_replicate│
        └───────────┘          └────────────┘  └────────────┘         └────────────┘
             Providers extend this module

Installation
============

What to Install
---------------

This module is **auto-installed** as a dependency. You typically don't install it directly.

**For AI chat features, install:**

.. code-block:: bash

    odoo-bin -d your_db -i llm_assistant,llm_openai

This Module Provides
--------------------

- Provider abstraction framework
- Model and publisher management
- Enhanced ``mail.message`` with ``llm_role`` field
- Security groups and access control
- Base configuration menus

Modules That Depend on This
---------------------------

+-----------------+----------------------------------------------------------------+
| Category        | Modules                                                        |
+=================+================================================================+
| **Interfaces**  | ``llm_assistant``, ``llm_thread``, ``llm_mcp_server``          |
+-----------------+----------------------------------------------------------------+
| **Providers**   | ``llm_openai``, ``llm_ollama``, ``llm_mistral``, etc.          |
+-----------------+----------------------------------------------------------------+
| **Infrastructure** | ``llm_tool``, ``llm_store``, ``llm_generate``               |
+-----------------+----------------------------------------------------------------+

Common Setups
-------------

+---------------------------+----------------------------------------------+
| I want to...              | Install                                      |
+===========================+==============================================+
| Chat with AI in Odoo      | ``llm_assistant`` + ``llm_openai``           |
+---------------------------+----------------------------------------------+
| Use local AI (privacy)    | ``llm_assistant`` + ``llm_ollama``           |
+---------------------------+----------------------------------------------+
| Add RAG/knowledge base    | Above + ``llm_knowledge`` + ``llm_pgvector`` |
+---------------------------+----------------------------------------------+

Overview
========

The LLM Integration Base serves as the foundation for building AI-powered features across Odoo applications. It extends Odoo's core messaging system with AI-specific capabilities.

Core Capabilities
-----------------

- **Enhanced Messaging System** - AI-optimized message handling with 10x performance improvement
- **Provider Abstraction** - Unified interface for multiple AI services
- **Model Management** - Centralized catalog of AI models with capabilities
- **Security Framework** - Role-based access control and API key management

Key Features
============

Enhanced Mail Message System
----------------------------

.. code-block:: python

    # Performance-optimized role field (10x faster queries)
    llm_role = fields.Selection([
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('tool', 'Tool'),
        ('system', 'System')
    ], store=True, index=True)

    # Structured data for tool messages
    body_json = fields.Json()

Provider Framework
------------------

.. code-block:: python

    # Dynamic method dispatch to service implementations
    provider._dispatch('chat', messages=messages, model=model)
    provider._dispatch('embedding', text=text)
    provider._dispatch('generate', prompt=prompt, type='image')

Technical Specifications
========================

Module Information
------------------

- **Name**: LLM Integration Base
- **Version**: 18.0.1.4.0
- **Category**: Technical
- **License**: LGPL-3
- **Dependencies**: ``mail``, ``web``
- **Author**: Apexive Solutions LLC

Key Models
----------

- **``llm.provider``**: AI service provider configuration
- **``llm.model``**: AI model registry
- **``llm.publisher``**: Model publisher tracking
- **``mail.message``** (extended): Enhanced with ``llm_role`` and ``body_json``

Related Modules
===============

- **``llm_assistant``** - AI assistants with prompt management
- **``llm_thread``** - Chat interfaces and conversation management
- **``llm_tool``** - Function calling and Odoo integration
- **``llm_openai``** - OpenAI provider implementation
- **``llm_ollama``** - Local model deployment

Resources
=========

- `GitHub Repository <https://github.com/apexive/odoo-llm>`_
- `Architecture Overview <../OVERVIEW.md>`_

License
=======

This module is licensed under `LGPL-3 <https://www.gnu.org/licenses/lgpl-3.0.html>`_.

----

*© 2025 Apexive Solutions LLC. All rights reserved.*
