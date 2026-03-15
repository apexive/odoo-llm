==========================================
Replicate Provider for Odoo LLM
==========================================

Access Replicate's model marketplace for image generation.

**Module Type:** 🔧 Provider (Image Generation)

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
              │       ★ llm_replicate (This Module) ★     │
              │          Replicate.com Provider           │
              │  🖼️ SDXL │ Flux │ Llama │ Model Marketplace │
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

**For image generation:**

.. code-block:: bash

    odoo-bin -d your_db -i llm_assistant,llm_replicate

Auto-Installed Dependencies
---------------------------

- ``llm`` (core infrastructure)

When to Use Replicate
---------------------

+------------------+-------------------------------+
| Feature          | Replicate                     |
+==================+===============================+
| **Model Variety**| 🎯 Huge marketplace           |
+------------------+-------------------------------+
| **Image Gen**    | ✅ SDXL, Flux, etc.           |
+------------------+-------------------------------+
| **Pay-per-use**  | 💳 Pay only what you use      |
+------------------+-------------------------------+

Common Setups
-------------

+-------------------------+----------------------------------------------+
| I want to...            | Install                                      |
+=========================+==============================================+
| Generate images         | ``llm_assistant`` + ``llm_replicate``        |
+-------------------------+----------------------------------------------+
| Chat + images           | ``llm_assistant`` + ``llm_openai`` +         |
|                         | ``llm_replicate``                            |
+-------------------------+----------------------------------------------+

Features
========

- Connect to Replicate API with proper authentication
- Support for various AI models hosted on Replicate
- Text generation capabilities
- Automatic model discovery

Configuration
=============

1. Install the module
2. Navigate to **LLM > Configuration > Providers**
3. Create a new provider and select "Replicate" as the provider type
4. Enter your Replicate API key
5. Click "Fetch Models" to import available models

Technical Specifications
========================

- **Version**: 18.0.1.0.0
- **License**: LGPL-3
- **Dependencies**: ``llm``

Related Modules
===============

- **``llm``** - Core infrastructure
- **``llm_assistant``** - AI assistants
- **``llm_fal_ai``** - Alternative: FAL.ai (fast inference)
- **``llm_comfyui``** - Alternative: self-hosted ComfyUI

License
=======

LGPL-3

----

*© 2025 Apexive Solutions LLC*
