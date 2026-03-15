# LLM Generate Job

This module provides a comprehensive generation job management system for LLM providers, extending the base LLM functionality with advanced queue management and job tracking capabilities.

**Module Type:** 🔌 Extension

![Architecture](static/description/llm_generate_job_architecture.png)

## Installation

### What to Install

Install this module when you need **background/async generation** for long-running tasks.

```bash
odoo-bin -d your_db -i llm_generate_job
```

### Auto-Installed Dependencies

These are pulled in automatically:

- `llm_generate` (generation API)
- `llm_thread` (chat interface)
- `llm_tool` (tool framework)
- `llm` (core infrastructure)

### When to Use This Module

| Scenario                  | Recommendation                     |
| ------------------------- | ---------------------------------- |
| Quick chat responses      | Not needed - use direct generation |
| Long document generation  | **Install this**                   |
| Batch image generation    | **Install this**                   |
| API rate limit management | **Install this**                   |

### Common Setups Using This Module

| I want to...               | Install                                             |
| -------------------------- | --------------------------------------------------- |
| Background text generation | `llm_assistant` + `llm_openai` + `llm_generate_job` |
| Batch image processing     | `llm_assistant` + `llm_fal_ai` + `llm_generate_job` |
| Queue management dashboard | `llm_generate_job` (adds admin views)               |

## Features

### Generation Job Management

- **Job Lifecycle**: Complete job lifecycle management from creation to completion
- **Status Tracking**: Real-time job status monitoring (draft, queued, running, completed, failed, cancelled)
- **Retry Logic**: Automatic and manual retry capabilities for failed jobs
- **Error Handling**: Comprehensive error tracking and reporting

### Queue Management

- **Provider-specific Queues**: Each LLM provider has its own dedicated queue
- **Concurrent Job Control**: Configurable maximum concurrent jobs per provider
- **Queue Health Monitoring**: Real-time queue health indicators (healthy, warning, critical)
- **Performance Metrics**: Queue performance analytics and success rates

### Flexible Generation Options

- **Direct Generation**: Traditional immediate generation (backward compatible)
- **Queued Generation**: Advanced queue-based generation for better resource management
- **Auto-detection**: Intelligent choice between direct and queued generation based on provider capabilities

### Monitoring and Analytics

- **Job Statistics**: Comprehensive job statistics and performance metrics
- **Queue Analytics**: Queue performance monitoring and capacity planning
- **Success Rate Tracking**: Success rate monitoring across providers and time periods
- **Duration Tracking**: Queue time and processing time analytics

## Architecture

### Models

#### `llm.generation.job`

The main model for managing individual generation jobs:

- **Relationships**: Links to thread, provider, model, and messages
- **Status Management**: Job state transitions and lifecycle management
- **Timing**: Queue time, processing time, and completion tracking
- **Retry Logic**: Configurable retry attempts and error handling

#### `llm.generation.queue`

Provider-specific queue management:

- **Configuration**: Maximum concurrent jobs, auto-retry settings
- **Monitoring**: Real-time job counts and queue health
- **Performance**: Success rates and processing time analytics
- **Actions**: Queue processing, job retries, and maintenance

### Thread Integration

Extends `llm.thread` with:

- **Generation Options**: `generate_response()` method with `use_queue` parameter
- **Job Tracking**: Links to all generation jobs for the thread
- **Status Monitoring**: Real-time generation status and progress
- **Statistics**: Thread-level generation analytics

### Provider Integration

Extends `llm.provider` with:

- **Job Creation**: `create_generation_job()` method
- **Status Checking**: `check_generation_job_status()` method
- **Job Cancellation**: `cancel_generation_job()` method
- **Queue Information**: `get_generation_queue_info()` method

## Usage

### Basic Usage

```python
# Direct generation (backward compatible)
thread = self.env['llm.thread'].browse(thread_id)
for update in thread.generate_response("Hello, how are you?", use_queue=False):
    print(update)

# Queued generation
for update in thread.generate_response("Hello, how are you?", use_queue=True):
    print(update)

# Auto-detection (recommended)
for update in thread.generate_response("Hello, how are you?"):
    # Will automatically choose based on provider capabilities
    print(update)
```

### Queue Management

```python
# Get or create queue for a provider
queue = self.env['llm.generation.queue']._get_or_create_queue(provider_id)

# Process pending jobs
processed_count = queue._process_provider_queue(provider)

# Check queue health
stats = queue.get_queue_stats()
```

### Job Management

```python
# Create a job
job = self.env['llm.generation.job'].create({
    'thread_id': thread_id,
    'provider_id': provider_id,
    'model_id': model_id,
    'generation_inputs': {'prompt': 'Hello world'},
})

# Queue and start the job
job.action_queue()

# Monitor job status
while job.state in ['queued', 'running']:
    status = job.check_status()
    print(f"Job {job.id} is {job.state}")
```

## Configuration

### Queue Configuration

Each provider queue can be configured with:

- **Max Concurrent Jobs**: Maximum number of simultaneous jobs
- **Auto Retry**: Automatic retry of failed jobs
- **Retry Delay**: Time to wait before retrying failed jobs

### Job Configuration

Jobs support:

- **Max Retries**: Maximum number of retry attempts
- **Generation Inputs**: Custom inputs for the generation process
- **Provider Data**: Provider-specific configuration and metadata

## Monitoring

### Queue Health

Queues are automatically monitored for:

- **Healthy**: Normal operation
- **Warning**: High load but functioning
- **Critical**: Overloaded or failing
- **Disabled**: Manually disabled

### Performance Metrics

- **Average Queue Time**: Time jobs spend waiting
- **Average Processing Time**: Time jobs spend processing
- **Success Rate**: Percentage of successful jobs
- **Throughput**: Jobs processed per time period

## Administration

### Views

- **Generation Jobs**: List and manage all generation jobs
- **Generation Queues**: Monitor and configure provider queues
- **Queue Dashboard**: Real-time queue monitoring

### Cron Jobs

- **Process Queues**: Automatically process pending jobs (every minute)
- **Check Job Status**: Update running job statuses (every 30 seconds)
- **Auto-retry Failed Jobs**: Retry eligible failed jobs (every 5 minutes)
- **Cleanup Old Jobs**: Remove old completed jobs (daily)

## Provider Implementation

To implement generation job support in a provider:

```python
class MyProvider(models.Model):
    _inherit = 'llm.provider'

    def create_generation_job(self, job_record):
        # Create job with external provider
        external_job_id = self.my_api.create_job(
            job_record.generation_inputs
        )
        return external_job_id

    def check_generation_job_status(self, job_record):
        # Check job status with external provider
        status = self.my_api.get_job_status(job_record.external_job_id)

        if status['completed']:
            # Create result message
            message = job_record.thread_id.message_post(
                body=status['result'],
                llm_role='assistant',
                author_id=False,
            )
            return {
                'state': 'completed',
                'output_message_id': message.id,
            }
        elif status['failed']:
            return {
                'state': 'failed',
                'error_message': status['error'],
            }
        else:
            return {'state': 'running'}

    def cancel_generation_job(self, job_record):
        # Cancel job with external provider
        return self.my_api.cancel_job(job_record.external_job_id)
```

## Migration from Direct Generation

The module is fully backward compatible. Existing code using `thread.generate()` will continue to work without modification. To enable queue-based generation, simply set `use_queue=True` or let the system auto-detect based on provider capabilities.

## Security

- **User Access**: Users can create and view their own generation jobs
- **Manager Access**: LLM managers can view and manage all jobs and queues
- **Queue Management**: Only managers can configure and control queues

## Performance Considerations

- **Queue Processing**: Queues are processed every minute by default
- **Status Checking**: Job statuses are checked every 30 seconds
- **Cleanup**: Old jobs are automatically cleaned up after 7 days
- **Concurrent Jobs**: Configure max concurrent jobs based on provider limits

## Dependencies

- `llm_thread`: Core thread functionality
- `llm_tool`: Tool system integration
- `web_json_editor`: JSON field editing (optional)
