==========================================
FAL.ai Provider for Odoo LLM
==========================================

Fast image and video generation with Flux models.

**Module Type:** 🔧 Provider (Fast Image/Video Generation)

Architecture
============

::

    ┌───────────────────────────────────────────────────────┐
    │             Used By (Generation Modules)              │
    │     ┌─────────────┐           ┌───────────┐          │
    │     │llm_assistant│           │llm_generate│          │
    │     └──────┬──────┘           └─────┬─────┘          │
    └────────────┼────────────────────────┼────────────────┘
                 └────────────┬───────────┘
                              ▼
              ┌───────────────────────────────────────────┐
              │        ★ llm_fal_ai (This Module) ★       │
              │            FAL.ai Provider                │
              │  ⚡ Fast │ Flux │ Video │ Real-time       │
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

**For fast image generation:**

.. code-block:: bash

    odoo-bin -d your_db -i llm_assistant,llm_fal_ai

Auto-Installed Dependencies
---------------------------

- ``llm`` (core infrastructure)

Why Choose FAL.ai?
------------------

+------------------+-------------------------------+
| Feature          | FAL.ai                        |
+==================+===============================+
| **Speed**        | ⚡ Very fast inference        |
+------------------+-------------------------------+
| **Flux Models**  | ✅ Best Flux support          |
+------------------+-------------------------------+
| **Video**        | ✅ Video generation           |
+------------------+-------------------------------+
| **Real-time**    | ✅ Real-time generation       |
+------------------+-------------------------------+

Common Setups
-------------

+-------------------------+----------------------------------------------+
| I want to...            | Install                                      |
+=========================+==============================================+
| Fast image generation   | ``llm_assistant`` + ``llm_fal_ai``           |
+-------------------------+----------------------------------------------+
| Chat + fast images      | ``llm_assistant`` + ``llm_openai`` +         |
|                         | ``llm_fal_ai``                               |
+-------------------------+----------------------------------------------+

Features
========

- Connect to Fal.ai API with proper authentication
- Support for multiple generative AI models hosted on Fal.ai
- Text-to-image, text-to-video, and audio synthesis capabilities
- Automatic model discovery and filtering
- Async-friendly requests for long-running tasks

Configuration
=============

1. Install the module
2. Navigate to **LLM > Configuration > Providers**
3. Create a new provider and select "Fal.ai" as the provider type
4. Enter your Fal.ai API key
5. Click "Fetch Models" to import available models

Technical Specifications
========================

- **Version**: 18.0.1.0.0
- **License**: LGPL-3
- **Dependencies**: ``llm``
- **Python Package**: ``aiohttp`` (for async inference)

Related Modules
===============

- **``llm``** - Core infrastructure
- **``llm_assistant``** - AI assistants
- **``llm_replicate``** - Alternative: Replicate marketplace
- **``llm_comfyui``** - Alternative: self-hosted ComfyUI

License
=======

LGPL-3

----

*© 2025 Apexive Solutions LLC*
