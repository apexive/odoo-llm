# LLM Training Module

Manage LLM fine-tuning jobs across different providers directly from Odoo.

**Module Type:** 🔌 Extension (Model Fine-tuning)

## Architecture

```
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
```

## Installation

### What to Install

**For model fine-tuning:**

```bash
odoo-bin -d your_db -i llm_training
```

### Auto-Installed Dependencies

- `llm` (core infrastructure)

### Why Use Training?

| Feature            | llm_training               |
| ------------------ | -------------------------- |
| **Management**     | 📊 Manage jobs from Odoo   |
| **Datasets**       | 📁 Dataset organization    |
| **Monitoring**     | 📈 Track job progress      |
| **Multi-provider** | 🔄 Works with OpenAI, etc. |

### Common Setups

| I want to...      | Install                                         |
| ----------------- | ----------------------------------------------- |
| Fine-tune models  | `llm_training` + `llm_openai`                   |
| Full LLM workflow | `llm_assistant` + `llm_openai` + `llm_training` |

This module provides functionality for managing LLM fine-tuning jobs across different providers. It allows users to create, monitor, and manage fine-tuning jobs directly from the Odoo interface.

## Features

- Create and manage fine-tuning jobs for LLMs
- Track job status and metrics
- Support for multiple LLM providers (OpenAI, etc.)
- Integration with dataset management
- Job status monitoring and notifications

## Usage

### Accessing the Module

1. Navigate to **LLM > Training > Jobs** in the main menu
2. This will display the list of all training jobs with their current status

### Creating a New Training Job

1. Click the **Create** button on the training jobs list view
2. Fill in the required fields:
   - **Name**: A descriptive name for the job
   - **Provider**: Select the LLM provider (e.g., OpenAI)
   - **Base Model**: Select the base model to fine-tune
   - **Datasets**: Add one or more datasets to use for training
3. Optionally configure:
   - **Description**: Add details about the job
   - **Hyperparameters**: Adjust training parameters in JSON format
4. Click **Save** to create the job in draft state
5. Click **Submit** to start the training process

### Monitoring Job Status

1. The job will progress through several states:

   - **Draft**: Initial state
   - **Validating**: Validating datasets
   - **Preparing**: Preparing data for training
   - **Queued**: Job is queued with the provider
   - **Training**: Training is in progress
   - **Completed**: Training completed successfully
   - **Failed**: Training failed
   - **Cancelled**: Training was cancelled

2. For jobs in progress, click the **Check Status** button to update the status

### Viewing Results

1. Once a job is completed, go to the **Results** tab
2. Here you can find:
   - The resulting fine-tuned model
   - Training metrics
   - Training logs

### Using Fine-tuned Models

After successful training, the fine-tuned model will be automatically added to your available models and can be used in:

- LLM Threads
- LLM Agents
- Any other component that uses LLM models

## Security

The module follows the standard two-tier security model:

- Regular users (base.group_user) have read-only access
- LLM Managers (llm.group_llm_manager) have full CRUD access

## Technical Information

### Model Structure

- `llm.training.job`: Main model for training jobs
- `llm.training.dataset`: Model for managing training datasets

### Provider Integration

The module uses a standardized interface for provider integration:

- `start_training_job`: Initiates the training process
- `check_training_job_status`: Checks the current status
- `cancel_training_job`: Cancels an ongoing job

Providers implement these methods to handle provider-specific logic.

## Troubleshooting

### Common Issues

1. **Job stuck in validating state**:

   - Check that datasets are properly formatted
   - Verify provider credentials

2. **Failed jobs**:

   - Check the Results tab for error details
   - Verify hyperparameters are correctly formatted

3. **Missing models after completion**:
   - Use the Check Status button to refresh the job status
   - Verify provider access to the fine-tuned model

## Contributing

Please follow the standard Odoo development guidelines when contributing to this module.
