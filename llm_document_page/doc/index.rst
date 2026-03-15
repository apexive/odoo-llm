==========================================
Document Page Integration for Odoo LLM
==========================================

AI-powered document assistance for Odoo Document Pages.

**Module Type:** 🔌 Extension (Document Pages)

Architecture
============

::

    ┌───────────────────────────────────────────────────────────────┐
    │                      Application Layer                        │
    │                    ┌───────────────┐                          │
    │                    │Document Pages │                          │
    │                    │     (OCA)     │                          │
    │                    └───────┬───────┘                          │
    └────────────────────────────┼──────────────────────────────────┘
                                 │
                                 ▼
                  ┌───────────────────────────────────────────┐
                  │  ★ llm_document_page (This Module) ★      │
                  │     Document Page + LLM Integration       │
                  │  📄 Smart Content │ AI Suggestions        │
                  └─────────────────────┬─────────────────────┘
                                        │
                                        ▼
                  ┌───────────────────────────────────────────┐
                  │                   llm                     │
                  │            (Core Base Module)             │
                  └───────────────────────────────────────────┘

Installation
============

What to Install
---------------

**For AI-assisted document pages:**

.. code-block:: bash

    odoo-bin -d your_db -i llm_document_page

Auto-Installed Dependencies
---------------------------

- ``llm`` (core infrastructure)
- ``knowledge_document_page`` (OCA document pages)

Why Use This Module?
--------------------

+------------------+-------------------------------+
| Feature          | llm_document_page             |
+==================+===============================+
| **Suggestions**  | 🤖 AI-powered content         |
+------------------+-------------------------------+
| **Integration**  | 📄 Native document pages      |
+------------------+-------------------------------+
| **Generation**   | ✍️ Smart content generation   |
+------------------+-------------------------------+

Common Setups
-------------

+-------------------------+----------------------------------------------+
| I want to...            | Install                                      |
+=========================+==============================================+
| AI document pages       | ``llm_document_page`` + ``llm_openai``       |
+-------------------------+----------------------------------------------+
| Chat + doc pages        | ``llm_assistant`` + ``llm_openai`` +         |
|                         | ``llm_document_page``                        |
+-------------------------+----------------------------------------------+

Features
========

- AI-powered document suggestions
- Document page integration
- Smart content generation
- Intelligent editing assistance

Usage
=====

Access LLM features directly from document pages for intelligent content assistance.

Technical Specifications
========================

- **Version**: 18.0.1.0.0
- **License**: LGPL-3
- **Dependencies**: ``llm``, ``knowledge_document_page``

Related Modules
===============

- **``llm``** - Core infrastructure
- **``llm_assistant``** - AI assistants
- **``knowledge_document_page``** - OCA document pages

License
=======

LGPL-3

----

*© 2025 Apexive Solutions LLC*
