# LLM Prompt Templates Module

This Odoo module provides functionality for creating and managing reusable prompt templates for Large Language Model (LLM) interactions. It allows you to define structured prompts with dynamic arguments, organize them with categories and tags, and use them across your Odoo instance.

## Version 16.0.1.3.0 - New Features

### Enhanced Prompt Testing Wizard
- **Universal Record Selection**: Test prompts with any record from any model in your Odoo instance
- **Improved UI**: Cleaner, more compact interface with better organization
- **Real-time Context Updates**: Automatic context population when selecting related records
- **Multiple Output Formats**: View generated messages in JSON, YAML, or readable text format
- **Sample Data Population**: Automatically populate test context with common fields from selected records

### Chat Interface Integration
- **Prompt Dropdown**: Select prompts directly from the chat interface
- **Thread-Prompt Association**: Link specific prompts to chat threads for consistent workflows
- **Related Record Context**: Automatic integration of related record data in chat prompts

### Template Format Flexibility
- **Multiple Formats**: Support for Text, YAML, and JSON template formats
- **Auto-detection**: Automatic argument detection from template content
- **Format Validation**: Built-in validation for YAML and JSON templates

## Features

- **Reusable Prompt Templates**: Create and manage prompt templates that can be reused across your LLM interactions.
- **Dynamic Arguments**: Define arguments within prompts using the `{{argument_name}}` syntax for dynamic content insertion.
- **Multi-step Prompt Workflows**: Create complex prompt sequences with different roles (system, user, assistant).
- **Categorization and Tagging**: Organize prompts with categories and tags for easy discovery.
- **Prompt Testing**: Test prompts directly from the interface to verify they work as expected.
- **API Integration**: Use prompts programmatically through the provided API endpoints.

## Installation

1. Clone the repository into your Odoo addons directory.
2. Install the module via the Odoo Apps menu.

## Configuration

### Creating Prompt Templates

1. Navigate to **LLM → Prompts** menu item in your Odoo instance.
2. Click on **Create** to create a new prompt template.
3. Fill in the following fields:
   - **Name**: A unique identifier for the prompt
   - **Description**: A human-readable description
   - **Category**: Select or create a category for organization
   - **Tags**: Add tags for classification
   - **Arguments Schema**: Define the JSON schema for arguments (optional)
   - **Templates**: Add one or more templates with different roles:
     - **System**: For setting context and instructions
     - **User**: For user messages
     - **Assistant**: For assistant responses

### Arguments Schema

The arguments schema defines the structure of arguments that can be used in the prompt templates. It follows a JSON format:

```json
{
  "customer_name": {
    "type": "string",
    "description": "Name of the customer",
    "required": true
  },
  "product_list": {
    "type": "array",
    "description": "List of products",
    "required": false
  }
}
```

### Using Prompts in Code

```python
# Get a prompt by name
prompt = env['llm.prompt'].search([('name', '=', 'customer_greeting')], limit=1)

# Generate messages with arguments
messages = prompt.generate_messages({
    'customer_name': 'John Doe',
    'product_list': ['Product A', 'Product B']
})

# Use the messages with an LLM provider
response = env['llm.provider'].get_default().generate_text(messages=messages)
```

## Dependencies

- Odoo 16.0 or later
- Python 3.8 or later
- Base LLM module (`llm`)

## Security

The module follows Odoo's standard security model:

- Regular users can view and use prompts
- LLM Managers have full access to create, edit, and delete prompts and their configurations

## License

This module is licensed under the LGPL-3 license.
