# LLM Generate for Odoo

Unified content generation system with dynamic form generation, streaming responses, and race condition fixes. This module provides a clean, consistent API for generating all types of content (text, images, audio, etc.) across different AI providers.

**Module Type:** 📦 Infrastructure

![Architecture](static/description/llm_generate_architecture.png)

## Installation

### What to Install

This module is typically **auto-installed** as a dependency of `llm_thread` or `llm_assistant`.

**For content generation features:**

```
llm_assistant + llm_openai (or other provider)
```

### Auto-Installed Dependencies

These are pulled in automatically:

- `llm` (core infrastructure)
- `llm_assistant` (assistant framework)
- `mail` (Odoo messaging)

### Optional Enhancements

| Module             | Adds                                              |
| ------------------ | ------------------------------------------------- |
| `llm_generate_job` | Background job queue for long-running generations |
| `llm_fal_ai`       | Fast image generation                             |
| `llm_replicate`    | Model marketplace access                          |

### Common Setups Using This Module

| I want to...           | Install                                             |
| ---------------------- | --------------------------------------------------- |
| Generate text with GPT | `llm_assistant` + `llm_openai`                      |
| Generate images        | `llm_assistant` + `llm_fal_ai` (or `llm_replicate`) |
| Background generation  | Above + `llm_generate_job`                          |

## Overview

The LLM Generate module serves as the unified interface for all content generation operations in the Odoo LLM ecosystem. It provides a consistent API regardless of the underlying AI provider or content type, with advanced features like dynamic form generation, streaming responses, and comprehensive error handling.

### Core Capabilities

- **Unified Generation API** - Single interface for text, image, audio, and other content types
- **Dynamic Form Generation** - Automatic UI generation based on model schemas
- **Streaming Generation** - Real-time content creation with live updates
- **Race Condition Fixes** - Comprehensive async handling and loading state management
- **Schema Handling** - Intelligent schema resolution and form field generation
- **Queue Management** - Background processing for long-running generations

## Key Features

### Unified Generation Interface

**Single Method for All Content Types:**

```python
# Text generation
response = thread.generate_response(
    user_input="Write a product description",
    generation_type="text"
)

# Image generation
image = thread.generate_response(
    user_input="A beautiful landscape with mountains",
    generation_type="image",
    model_id=dalle_model.id
)

# Audio generation
audio = thread.generate_response(
    user_input="Convert this text to speech: Hello world",
    generation_type="audio"
)
```

### Dynamic Form Generation

**Automatic UI Creation from Model Schemas:**

The system automatically generates forms based on AI model input schemas:

```python
def get_input_schema(self):
    """Generate form schema with intelligent priority resolution"""
    # Priority order:
    # 1. Assistant's prompt schema (if assistant selected)
    # 2. Thread's direct prompt schema (if prompt directly selected)
    # 3. Model's default schema

    if self.assistant_id and self.assistant_id.prompt_id:
        return self.assistant_id.prompt_id.input_schema_json
    elif self.prompt_id:
        return self.prompt_id.input_schema_json
    else:
        return self.model_id.get_default_schema()
```

**Schema-Driven Form Fields:**

```javascript
// Automatic form field generation
get formFields() {
    const schema = this.inputSchema;
    if (!schema?.properties) return [];

    return Object.entries(schema.properties).map(([key, field]) => ({
        name: key,
        type: this.getFieldType(field),
        label: field.title || key,
        required: schema.required?.includes(key),
        default: field.default,
        placeholder: field.description
    }));
}
```

### Race Condition Fixes

**Comprehensive Async Handling:**

Fixed multiple race conditions in form loading and schema computation:

```javascript
// Before - Race condition prone
async _handleContextChange() {
    await this._loadThreadConfiguration();
    this._initializeFormValues(); // Could execute before schema loaded
}

// After - Proper async handling
async _handleContextChange() {
    this.state.isLoading = true;
    try {
        await this._loadThreadConfiguration();
        this._initializeFormValues();
    } finally {
        this.state.isLoading = false;
    }
}
```

**Loading State Management:**

- Proper loading indicators during async operations
- Prevention of premature form rendering
- Smooth user experience without UI flashing
- Consistent form behavior across scenarios

### Streaming Generation

**Real-time Content Creation:**

```python
def generate_response_stream(self, user_input, **kwargs):
    """Generate content with real-time streaming updates"""

    # Create placeholder message
    message = self.message_post(
        body="",
        llm_role="assistant"
    )

    # Stream content generation
    stream = self.provider_id.generate_stream(
        prompt=user_input,
        model=self.model_id.name,
        **kwargs
    )

    # Update message in real-time
    for chunk in stream:
        message.body += chunk.content
        self._notify_message_update(message)

    return message
```

**Frontend Streaming Support:**

```javascript
// Real-time UI updates during generation
async _streamGeneration(generationData) {
    const response = await this.rpc({
        route: '/llm/generate/stream',
        params: generationData
    });

    // Listen for real-time updates
    this.env.bus.addEventListener('llm_message_update', (event) => {
        this._updateStreamingMessage(event.detail);
    });
}
```

### Schema Source Transparency

**Clear Schema Source Indication:**

```javascript
get schemaSource() {
    if (this.state.isLoading) {
        return { type: 'loading', name: 'Loading...' };
    }

    if (this.thread?.assistant_id?.prompt_id) {
        return {
            type: 'prompt',
            name: this.thread.assistant_id.prompt_id.name,
            source: 'Assistant Prompt'
        };
    }

    if (this.thread?.prompt_id) {
        return {
            type: 'prompt',
            name: this.thread.prompt_id.name,
            source: 'Thread Prompt'
        };
    }

    if (this.thread?.model_id) {
        return {
            type: 'model',
            name: this.thread.model_id.name,
            source: 'Model Default'
        };
    }

    return { type: 'none', name: 'No Schema Available' };
}
```

**Visual Schema Indicators:**

- Badge showing schema source type (Prompt/Model/None)
- Clear indication of which configuration is being used
- Warning messages when no schema is available
- Tooltips explaining schema precedence

## Content Generation Types

### Text Generation

```python
# Simple text generation
text_response = env['llm.thread'].generate_content(
    prompt="Write a professional email",
    content_type="text",
    parameters={
        'temperature': 0.7,
        'max_tokens': 500
    }
)

# Template-based generation
templated_response = env['llm.thread'].generate_from_template(
    template_id=email_template.id,
    context={
        'recipient_name': 'John Doe',
        'company_name': 'Acme Corp',
        'product_name': 'Enterprise Suite'
    }
)
```

### Image Generation

```python
# Image generation with parameters
image_result = env['llm.thread'].generate_content(
    prompt="A modern office building at sunset",
    content_type="image",
    parameters={
        'size': '1024x1024',
        'style': 'photorealistic',
        'quality': 'high'
    }
)

# Batch image generation
batch_images = env['llm.thread'].generate_batch(
    prompts=[
        "Product photo - laptop on desk",
        "Product photo - laptop in meeting room",
        "Product photo - laptop outdoor setting"
    ],
    content_type="image",
    batch_size=3
)
```

### Multi-modal Generation

```python
# Combined text and image generation
multimodal_result = env['llm.thread'].generate_content(
    prompt="Create a product listing with description and image",
    content_type="multimodal",
    context={
        'product_name': 'Smart Watch Pro',
        'product_features': ['GPS', 'Heart Rate', 'Waterproof']
    }
)
```

## Queue Management

### Background Processing

```python
# Queue long-running generations
job = env['llm.generation.job'].create({
    'thread_id': thread.id,
    'prompt': "Generate comprehensive market analysis",
    'content_type': "text",
    'parameters': {'max_tokens': 4000},
    'priority': 'high'
})

# Monitor job progress
while job.state == 'running':
    time.sleep(1)
    job.refresh()

if job.state == 'completed':
    result = job.result_content
```

### Queue Configuration

```python
# Configure provider-specific queues
queue = env['llm.generation.queue'].create({
    'name': 'High Priority Text Generation',
    'provider_id': openai_provider.id,
    'content_types': ['text', 'chat'],
    'max_concurrent': 5,
    'timeout': 300
})
```

## Form Generation Examples

### Dynamic Schema-Based Forms

**Automatic Field Generation:**

```javascript
// Schema definition
const schema = {
  properties: {
    style: {
      type: "string",
      enum: ["photorealistic", "artistic", "cartoon"],
      title: "Image Style",
      description: "Choose the visual style",
    },
    mood: {
      type: "string",
      title: "Mood",
      description: "Describe the desired mood",
    },
    resolution: {
      type: "string",
      enum: ["512x512", "1024x1024", "1024x1792"],
      default: "1024x1024",
      title: "Resolution",
    },
  },
  required: ["style", "mood"],
};

// Automatic form generation creates:
// - Select field for style (with enum options)
// - Text input for mood (with description placeholder)
// - Select field for resolution (with default selected)
// - Required field validation
```

### Custom Form Components

```javascript
// Custom field types for specific use cases
const customFieldTypes = {
  color: ColorPickerField,
  slider: SliderField,
  file_upload: FileUploadField,
  model_selector: ModelSelectorField,
};

// Usage in schema
const advancedSchema = {
  properties: {
    primary_color: {
      type: "color",
      title: "Primary Color",
      default: "#3498db",
    },
    creativity: {
      type: "slider",
      minimum: 0,
      maximum: 1,
      step: 0.1,
      default: 0.7,
      title: "Creativity Level",
    },
  },
};
```

## Error Handling & Validation

### Comprehensive Error Management

```python
def generate_with_validation(self, prompt, **kwargs):
    """Generate content with comprehensive error handling"""
    try:
        # Validate inputs
        self._validate_generation_inputs(prompt, **kwargs)

        # Check provider availability
        if not self.provider_id.is_available():
            raise UserError("Provider is currently unavailable")

        # Validate content type support
        if not self.model_id.supports_content_type(kwargs.get('content_type')):
            raise UserError(f"Model doesn't support {kwargs.get('content_type')}")

        # Generate content
        return self._generate_content(prompt, **kwargs)

    except ValidationError as e:
        self._log_generation_error(e, 'validation')
        raise UserError(f"Validation failed: {e}")

    except APIError as e:
        self._log_generation_error(e, 'api')
        return self._handle_api_error(e)

    except Exception as e:
        self._log_generation_error(e, 'unknown')
        raise UserError("An unexpected error occurred during generation")
```

### Frontend Validation

```javascript
// Real-time form validation
_validateForm() {
    const errors = [];
    const values = this.state.formValues;
    const schema = this.inputSchema;

    // Required field validation
    schema.required?.forEach(field => {
        if (!values[field]) {
            errors.push(`${field} is required`);
        }
    });

    // Type validation
    Object.entries(schema.properties).forEach(([key, fieldSchema]) => {
        const value = values[key];
        if (value && !this._validateFieldType(value, fieldSchema)) {
            errors.push(`Invalid value for ${key}`);
        }
    });

    this.state.validationErrors = errors;
    return errors.length === 0;
}
```

## Integration Examples

### CRM Integration

```python
class CRMLead(models.Model):
    _inherit = 'crm.lead'

    def generate_follow_up_email(self):
        """Generate personalized follow-up email using AI"""
        thread = self.env['llm.thread'].create({
            'name': f'Follow-up Generation - {self.name}',
            'assistant_id': self.env.ref('crm_ai.follow_up_assistant').id,
            'model': self._name,
            'res_id': self.id
        })

        # Generate email content
        email_content = thread.generate_response(
            user_input="Generate follow-up email",
            context={
                'lead_name': self.name,
                'customer_name': self.partner_name,
                'last_contact': self.date_last_stage_update,
                'opportunity_value': self.expected_revenue
            }
        )

        return email_content
```

### Product Catalog Integration

```python
class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def generate_marketing_content(self, content_types=['description', 'image']):
        """Generate marketing content for product"""
        results = {}

        for content_type in content_types:
            if content_type == 'description':
                results['description'] = self._generate_description()
            elif content_type == 'image':
                results['image'] = self._generate_product_image()
            elif content_type == 'ad_copy':
                results['ad_copy'] = self._generate_ad_copy()

        return results

    def _generate_product_image(self):
        """Generate product marketing image"""
        prompt = f"""
        Product photography for {self.name}:
        - Category: {self.categ_id.name}
        - Key features: {', '.join(self.attribute_line_ids.mapped('display_name'))}
        - Professional, commercial style
        - Clean background, good lighting
        """

        return self.env['llm.thread'].generate_content(
            prompt=prompt,
            content_type="image",
            parameters={
                'size': '1024x1024',
                'style': 'commercial',
                'quality': 'high'
            }
        )
```

## API Reference

### Core Generation Methods

```python
# Basic generation
def generate_response(self, user_input, generation_type="text", **kwargs):
    """Main generation method with unified interface"""

# Streaming generation
def generate_response_stream(self, user_input, **kwargs):
    """Generate with real-time streaming updates"""

# Template-based generation
def generate_from_template(self, template_id, context, **kwargs):
    """Generate using prompt template with context"""

# Batch generation
def generate_batch(self, prompts, content_type, **kwargs):
    """Generate multiple items in batch"""

# Queue-based generation
def generate_async(self, prompt, **kwargs):
    """Queue generation for background processing"""
```

### Schema Methods

```python
# Get input schema for forms
def get_input_schema(self):
    """Get schema for dynamic form generation"""

# Validate schema compatibility
def validate_schema(self, schema):
    """Validate schema format and content"""

# Merge schemas from multiple sources
def merge_schemas(self, *schemas):
    """Combine schemas with intelligent merging"""
```

## Performance Optimizations

### Schema Caching

```python
@api.model
@tools.ormcache('model_id', 'prompt_id', 'assistant_id')
def _get_cached_schema(self, model_id, prompt_id, assistant_id):
    """Cache computed schemas for better performance"""
    return self._compute_input_schema()
```

### Streaming Optimizations

- **Chunked Processing**: Process generation in optimal chunks
- **UI Debouncing**: Prevent excessive UI updates during streaming
- **Memory Management**: Efficient handling of large content streams
- **Connection Pooling**: Reuse connections for better performance

## Technical Specifications

### Module Information

- **Name**: LLM Generate
- **Version**: 18.0.2.0.0
- **Category**: Productivity
- **License**: LGPL-3
- **Dependencies**: `llm`, `llm_assistant`, `mail`
- **Author**: Apexive Solutions LLC

### Key Models

- **`llm.generation.job`**: Background generation job management
- **`llm.generation.queue`**: Provider-specific queue configuration
- **Extensions to `llm.thread`**: Core generation methods

### Frontend Components

- **`LLMMediaForm`**: Dynamic form generation component
- **`LLMGenerationWizard`**: Generation parameter configuration
- **`LLMStreamingDisplay`**: Real-time content updates
- **`LLMSchemaIndicator`**: Schema source transparency

## Related Modules

- **`llm`**: Base infrastructure and provider framework
- **`llm_assistant`**: Assistant configuration and prompt templates
- **`llm_tool`**: Function calling and Odoo integration
- **`llm_generate_job`**: Advanced job queue management
- **`llm_fal_ai`**: FAL.ai provider with generate endpoint integration

## Support & Resources

- **Documentation**: [GitHub Repository](https://github.com/apexive/odoo-llm)
- **Architecture Guide**: [OVERVIEW.md](../OVERVIEW.md)
- **API Examples**: [Generation Examples](examples/)
- **Community**: [GitHub Discussions](https://github.com/apexive/odoo-llm/discussions)

## License

This module is licensed under [LGPL-3](https://www.gnu.org/licenses/lgpl-3.0.html).

---

_© 2025 Apexive Solutions LLC. All rights reserved._
