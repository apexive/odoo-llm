# LLM Generate Job

This Odoo module allows you to manage content generation jobs using Large Language Models (LLMs), especially for tasks that require asynchronous or long-running processing.

## What does this module do?

- **Generation job management:** Create, monitor, and control text, image, video, or other media generation jobs using a job queue.
- **Webhook support:** Define webhook URLs to receive automatic notifications when a generation job is completed.
- **Thread integration:** Job results can be delivered and integrated into conversation threads.
- **Multimedia support:** Manage queues for image, video, and other media generation.
- **Visibility control:** Control the visibility of jobs in Odoo's list (tree) views.

## Installation

1. Copy the `llm_generate_job` folder into your Odoo instance's addons directory.
2. Install the required dependencies: `base`, `mail`, `llm`, `llm_thread`, `llm_generate`, `llm_mail_message_subtypes`.
3. Install the module from the Odoo interface.

## Usage

- Access the LLM generation jobs menu.
- Create a new job, select the generation type, and configure the necessary parameters.
- Monitor the status and results of each job.
- Set up webhooks to receive automatic notifications when jobs are completed.

## Credits

- Author: Apexive Solutions LLC
- Repository: [https://github.com/apexive/odoo-llm](https://github.com/apexive/odoo-llm)

## License

LGPL-3
