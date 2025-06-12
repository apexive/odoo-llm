# LLM Generate Job Module

## Overview

The `llm_generate_job` module provides comprehensive management of long-running generation jobs for LLM (Large Language Model) operations in Odoo. It enables asynchronous processing of image, video, and other media generation tasks with webhook support for completion notifications.

## Features

### Core Functionality
- **Job Queue Management**: Complete lifecycle management of generation jobs with multiple states
- **Webhook Support**: Asynchronous completion notifications via secure webhook endpoints
- **Provider Integration**: Extensible framework for different AI service providers
- **Thread Integration**: Seamless integration with LLM threads for result delivery
- **State Management**: Comprehensive job states (draft, submitted, queued, processing, completed, failed, cancelled)

### Job States
- `draft`: Initial state when job is created
- `submitted`: Job has been submitted to the provider
- `queued`: Job is queued for processing by the provider
- `processing`: Job is currently being processed
- `completed`: Job completed successfully with results
- `failed`: Job failed with error information
- `cancelled`: Job was cancelled by user or system

### Security Features
- **Webhook Authentication**: Secure webhook signature verification (FAL AI support included)
- **Access Control**: Role-based permissions (users vs managers)
- **Secure API Endpoints**: Protected REST endpoints for job management

## Dependencies

### Odoo Modules
- `base`: Core Odoo functionality
- `mail`: Mail and messaging system
- `llm`: Base LLM functionality
- `llm_thread`: Thread management for conversations
- `llm_generate`: Generation capabilities
- `llm_mail_message_subtypes`: Message subtype management

### Python Packages
- `PyNaCl`: For webhook signature verification
- `requests`: HTTP client for API calls
- `fal_client`: FAL AI provider client (optional, for FAL AI integration)

## Installation

1. **Install Python Dependencies**:
   ```bash
   pip install PyNaCl requests fal-client
   ```

2. **Install Module**:
   - Place the module in your Odoo addons directory
   - Update the apps list in Odoo
   - Install the "LLM Generate Job" module

## Usage

### Creating Generation Jobs

```python
# Create a new generation job
job = self.env['llm.generate.job'].create({
    'name': 'Image Generation Task',
    'provider_id': provider.id,
    'thread_id': thread.id,
    'prompt': 'A beautiful sunset over mountains',
    'generation_type': 'image',
    'webhook_url': 'https://your-domain.com/webhook/fal_ai',
    'parameters': {'width': 1024, 'height': 1024}
})

# Submit the job
job.submit_job()
```

### Thread Integration

```python
# Create async generation job from thread
thread = self.env['llm.thread'].browse(thread_id)
job = thread.create_generation_job(
    provider_id=provider.id,
    prompt="Generate an image of a cat",
    generation_type='image',
    parameters={'style': 'realistic'}
)
```

### Provider Extension

To add support for new providers, extend the `llm.provider` model:

```python
class LLMProvider(models.Model):
    _inherit = 'llm.provider'
    
    def submit_generation_job_yourprovider(self, job):
        # Implement provider-specific job submission
        pass
    
    def check_job_status_yourprovider(self, job):
        # Implement provider-specific status checking
        pass
    
    def cancel_job_yourprovider(self, job):
        # Implement provider-specific job cancellation
        pass
```

## Configuration

### Webhook Setup

1. **Configure Provider**: Set up your AI provider credentials in the LLM Provider configuration
2. **Webhook URL**: The module automatically provides webhook endpoints at:
   - FAL AI: `/webhook/fal_ai`
   - Custom: Implement your own webhook controller

### Security Groups

- **LLM Job User**: Can view and manage their own jobs
- **LLM Job Manager**: Can manage all jobs and access advanced features

### Cron Jobs

The module includes automatic cleanup cron jobs:
- **Cleanup Completed Jobs**: Removes old completed jobs (configurable retention period)
- **Status Sync**: Periodically syncs job status with providers

## API Endpoints

### REST API

- `GET /api/llm/job/<int:job_id>/status`: Get job status
- `POST /api/llm/job/<int:job_id>/cancel`: Cancel a job
- `POST /api/llm/job/<int:job_id>/retry`: Retry a failed job

### Webhook Endpoints

- `POST /webhook/fal_ai`: FAL AI webhook receiver

## Views and Menus

### Available Views
- **Form View**: Detailed job information and management
- **Tree View**: List view with filtering and bulk actions
- **Kanban View**: Visual job board organized by state
- **Search View**: Advanced filtering and grouping options

### Menu Structure
```
LLM
├── Generation Jobs
│   ├── All Jobs
│   ├── My Jobs
│   └── Failed Jobs
```

## Customization

### Custom Job Types

Add custom generation types by extending the selection field:

```python
class LLMGenerateJob(models.Model):
    _inherit = 'llm.generate.job'
    
    generation_type = fields.Selection(
        selection_add=[('custom_type', 'Custom Type')],
        ondelete={'custom_type': 'cascade'}
    )
```

### Custom Result Processing

Override result processing for specific needs:

```python
def _process_job_result(self, result_data):
    # Custom result processing logic
    processed_result = super()._process_job_result(result_data)
    # Add custom processing
    return processed_result
```

## Troubleshooting

### Common Issues

1. **Webhook Not Receiving**: Check firewall and ensure webhook URL is accessible
2. **Job Stuck in Processing**: Verify provider API connectivity and credentials
3. **Permission Denied**: Ensure user has appropriate security group membership

### Debug Mode

Enable debug logging for detailed job processing information:

```python
# In odoo.conf
log_level = debug
log_handler = :DEBUG
```

## Support

For issues and feature requests, please refer to the module documentation or contact the development team.

## License

LGPL-3 License
