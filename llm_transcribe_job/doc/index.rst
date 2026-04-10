==============================
LLM Transcribe Job
==============================

Comprehensive transcription job management system with queue management and job tracking capabilities for long-running AI tasks.

**Module Type:** 🔌 Extension

.. image:: ../static/description/llm_generate_job_architecture.png
   :alt: LLM Transcribe Job Architecture
   :width: 100%

Installation
============

What to Install
---------------

Install this module when you need **background/async transcription** for long-running tasks.

.. code-block:: bash

    odoo-bin -d your_db -i llm_transcribe_job

Auto-Installed Dependencies
---------------------------

These are pulled in automatically:

- ``llm_transcribe`` (transcription API)
- ``llm_thread`` (chat interface)
- ``llm_tool`` (tool framework)
- ``llm`` (core infrastructure)

When to Use This Module
-----------------------

+----------------------------+------------------------------------------+
| Scenario                   | Recommendation                           |
+============================+==========================================+
| Quick chat responses       | Not needed - use direct transcription       |
+----------------------------+------------------------------------------+
| Long document transcription   | **Install this**                         |
+----------------------------+------------------------------------------+
| Batch audio transcription     | **Install this**                         |
+----------------------------+------------------------------------------+
| API rate limit management  | **Install this**                         |
+----------------------------+------------------------------------------+

Common Setups
-------------

+-----------------------------+------------------------------------------------------+
| I want to...                | Install                                              |
+=============================+======================================================+
| Background audio transcription | ``llm_assistant`` + ``llm_openai`` + this module     |
+-----------------------------+------------------------------------------------------+
| Batch audio processing      | ``llm_assistant`` + ``llm_fal_ai`` + this module     |
+-----------------------------+------------------------------------------------------+

Features
========

Transcription Job Management
-------------------------

- **Job Lifecycle**: Complete job lifecycle management from creation to completion
- **Status Tracking**: Real-time job status (draft, queued, running, completed, failed, cancelled)
- **Retry Logic**: Automatic and manual retry capabilities for failed jobs
- **Error Handling**: Comprehensive error tracking and reporting

Queue Management
----------------

- **Provider-specific Queues**: Each LLM provider has its own dedicated queue
- **Concurrent Job Control**: Configurable maximum concurrent jobs per provider
- **Queue Health Monitoring**: Real-time queue health indicators
- **Performance Metrics**: Queue performance analytics and success rates

Usage
=====

Basic Usage
-----------

.. code-block:: python

    # When the thread uses a transcription model, queueing is automatic
    thread = self.env['llm.thread'].browse(thread_id)
    user_message = thread.message_post(
        body="Please transcribe the attached audio.",
        llm_role="user",
        body_json={"attachment_ids": [attachment_id]},
    )

    for update in thread.generate_messages(user_message):
        print(update)

Job Management
--------------

.. code-block:: python

    # Create a job
    job = self.env['llm.transcription.job'].create({
        'thread_id': thread_id,
        'provider_id': provider_id,
        'model_id': model_id,
        'transcription_inputs': {'prompt': 'Hello world'},
    })

    # Queue and start the job
    job.action_queue()

    # Monitor job status
    while job.state in ['queued', 'running']:
        status = job.check_status()
        print(f"Job {job.id} is {job.state}")

Architecture
============

Models
------

``llm.transcription.job``
~~~~~~~~~~~~~~~~~~~~~~

The main model for managing individual transcription jobs:

- **Relationships**: Links to thread, provider, model, and messages
- **Status Management**: Job state transitions and lifecycle management
- **Timing**: Queue time, processing time, and completion tracking

``llm.transcription.queue``
~~~~~~~~~~~~~~~~~~~~~~~~

Provider-specific queue management:

- **Configuration**: Maximum concurrent jobs, auto-retry settings
- **Monitoring**: Real-time job counts and queue health
- **Performance**: Success rates and processing time analytics

Monitoring
==========

Queue Health
------------

Queues are automatically monitored for:

- **Healthy**: Normal operation
- **Warning**: High load but functioning
- **Critical**: Overloaded or failing
- **Disabled**: Manually disabled

Performance Metrics
-------------------

- **Average Queue Time**: Time jobs spend waiting
- **Average Processing Time**: Time jobs spend processing
- **Success Rate**: Percentage of successful jobs
- **Throughput**: Jobs processed per time period

Cron Jobs
---------

- **Process Queues**: Automatically process pending jobs (every minute)
- **Check Job Status**: Update running job statuses (every 30 seconds)
- **Auto-retry Failed Jobs**: Retry eligible failed jobs (every 5 minutes)
- **Cleanup Old Jobs**: Remove old completed jobs (daily)

Technical Specifications
========================

Module Information
------------------

- **Name**: LLM Generate Job
- **Version**: 18.0.1.0.0
- **Category**: Productivity
- **License**: LGPL-3
- **Dependencies**: ``llm_thread``, ``llm_tool``
- **Author**: Apexive Solutions LLC

Related Modules
===============

- **``llm_transcribe``** - Core transcription API (dependency)
- **``llm_thread``** - Chat interface integration
- **``llm_assistant``** - Assistant configuration
- **``llm_fal_ai``** - Provider with job-based transcription

Resources
=========

- `GitHub Repository <https://github.com/apexive/odoo-llm>`_

License
=======

This module is licensed under `LGPL-3 <https://www.gnu.org/licenses/lgpl-3.0.html>`_.

----

*© 2025 Apexive Solutions LLC. All rights reserved.*
