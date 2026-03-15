==========================================
LLM Training Module for Odoo
==========================================

Manage LLM fine-tuning jobs across providers.

**Module Type:** 🔌 Extension (Model Fine-tuning)

Architecture
============

::

    ┌───────────────────────────────────────────────────────────────┐
    │                       User Interface                          │
    │                 ┌─────────────────────────┐                   │
    │                 │  LLM > Training > Jobs  │                   │
    │                 └───────────┬─────────────┘                   │
    └─────────────────────────────┼─────────────────────────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────────────────┐
                  │      ★ llm_training (This Module) ★       │
                  │          Fine-tuning Management           │
                  │  📊 Datasets │ Jobs │ Model Training      │
                  └─────────────────────┬─────────────────────┘
                                        │
                            ┌───────────┴───────────┐
                            ▼                       ▼
        ┌───────────────────────────┐   ┌───────────────────────────┐
        │           llm             │   │   Provider APIs           │
        │    (Core Base Module)     │   │  (OpenAI Fine-tune API)   │
        └───────────────────────────┘   └───────────────────────────┘

Installation
============

What to Install
---------------

**For model fine-tuning:**

.. code-block:: bash

    odoo-bin -d your_db -i llm_training

Auto-Installed Dependencies
---------------------------

- ``llm`` (core infrastructure)

Why Use Training?
-----------------

+------------------+-------------------------------+
| Feature          | llm_training                  |
+==================+===============================+
| **Management**   | 📊 Manage jobs from Odoo      |
+------------------+-------------------------------+
| **Datasets**     | 📁 Dataset organization       |
+------------------+-------------------------------+
| **Monitoring**   | 📈 Track job progress         |
+------------------+-------------------------------+
| **Multi-provider**| 🔄 Works with OpenAI, etc.   |
+------------------+-------------------------------+

Common Setups
-------------

+-------------------------+----------------------------------------------+
| I want to...            | Install                                      |
+=========================+==============================================+
| Fine-tune models        | ``llm_training`` + ``llm_openai``            |
+-------------------------+----------------------------------------------+
| Full LLM workflow       | ``llm_assistant`` + ``llm_openai`` +         |
|                         | ``llm_training``                             |
+-------------------------+----------------------------------------------+

Features
========

- Create and manage fine-tuning jobs for LLMs
- Track job status and metrics
- Support for multiple LLM providers (OpenAI, etc.)
- Integration with dataset management
- Job status monitoring and notifications

Usage
=====

Creating a New Training Job
---------------------------

1. Navigate to **LLM > Training > Jobs**
2. Click **Create**
3. Fill in: Name, Provider, Base Model, Datasets
4. Optionally configure hyperparameters
5. Click **Save** then **Submit**

Monitoring Job Status
---------------------

Jobs progress through states:

- **Draft** → **Validating** → **Preparing** → **Queued** → **Training** → **Completed**

Click **Check Status** to update the status.

Technical Specifications
========================

- **Version**: 18.0.1.0.0
- **License**: LGPL-3
- **Dependencies**: ``llm``

Models
------

- ``llm.training.job``: Main model for training jobs
- ``llm.training.dataset``: Dataset management

Related Modules
===============

- **``llm``** - Core infrastructure
- **``llm_openai``** - OpenAI fine-tuning support
- **``llm_assistant``** - AI assistants

License
=======

LGPL-3

----

*© 2025 Apexive Solutions LLC*
