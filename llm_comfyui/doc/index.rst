==========================================
ComfyUI Provider for Odoo LLM
==========================================

Self-hosted image generation with custom workflows.

**Module Type:** 🔧 Provider (Self-Hosted Image Generation)

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
              │        ★ llm_comfyui (This Module) ★      │
              │           ComfyUI Provider                │
              │  🖥️ Self-hosted │ Custom Workflows │ GPU  │
              └─────────────────────┬─────────────────────┘
                        ┌───────────┴───────────┐
                        ▼                       ▼
    ┌───────────────────────────┐   ┌───────────────────────────┐
    │           llm             │   │     ComfyUI Server        │
    │    (Core Base Module)     │   │   (localhost:8188)        │
    └───────────────────────────┘   │   🖥️ Your GPU hardware    │
                                    └───────────────────────────┘

Installation
============

What to Install
---------------

**For self-hosted image generation:**

.. code-block:: bash

    # 1. Install ComfyUI on your server with GPU
    # See: https://github.com/comfyanonymous/ComfyUI

    # 2. Install the Odoo module
    odoo-bin -d your_db -i llm_comfyui

Auto-Installed Dependencies
---------------------------

- ``llm`` (core infrastructure)

Why Choose ComfyUI?
-------------------

+------------------+-------------------------------+
| Feature          | ComfyUI                       |
+==================+===============================+
| **Control**      | 🎛️ Custom workflows           |
+------------------+-------------------------------+
| **Cost**         | 💰 Your hardware (no API fees)|
+------------------+-------------------------------+
| **Privacy**      | 🔒 Data stays local           |
+------------------+-------------------------------+
| **Flexibility**  | ✅ Any model/workflow         |
+------------------+-------------------------------+

ComfyUI vs ComfyICU
-------------------

+-------------+---------------+------------------+
| Feature     | llm_comfyui   | llm_comfy_icu    |
+=============+===============+==================+
| **Hosting** | 🖥️ Self-hosted| ☁️ Cloud          |
+-------------+---------------+------------------+
| **GPU**     | Required      | Not needed       |
+-------------+---------------+------------------+
| **Setup**   | Complex       | Easy             |
+-------------+---------------+------------------+
| **Cost**    | Hardware      | Pay-per-use      |
+-------------+---------------+------------------+

Common Setups
-------------

+-------------------------+----------------------------------------------+
| I want to...            | Install                                      |
+=========================+==============================================+
| Self-hosted images      | ``llm_comfyui`` (+ ComfyUI server)           |
+-------------------------+----------------------------------------------+
| Chat + local images     | ``llm_assistant`` + ``llm_openai`` +         |
|                         | ``llm_comfyui``                              |
+-------------------------+----------------------------------------------+

Features
========

- Connect to any ComfyUI instance via its HTTP API
- Submit ComfyUI workflows for execution
- Retrieve generated images
- Integrate with the LLM framework for media generation

Configuration
=============

1. Go to **LLM > Configuration > Providers**
2. Create a new provider with service type "ComfyUI"
3. Set the API Base URL to your ComfyUI instance (e.g., ``http://localhost:8188``)
4. Optionally set an API key if your ComfyUI instance requires authentication
5. Create a model that uses this provider

Usage
=====

The module expects ComfyUI workflow JSON in the API format. You can obtain
this by using the "Save (API Format)" button in the ComfyUI interface
(requires "Dev mode options" to be enabled in settings).

Technical Specifications
========================

- **Version**: 18.0.1.0.0
- **License**: LGPL-3
- **Dependencies**: ``llm``

Related Modules
===============

- **``llm``** - Core infrastructure
- **``llm_assistant``** - AI assistants
- **``llm_comfy_icu``** - Cloud alternative (no GPU required)
- **``llm_fal_ai``** - Alternative: FAL.ai cloud

License
=======

LGPL-3

----

*© 2025 Apexive Solutions LLC*
