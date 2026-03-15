# LLM Assistant for Odoo

Advanced AI assistant management with integrated prompt templates, testing capabilities, and intelligent configuration orchestration. This module serves as the intelligence layer that defines how Odoo data connects to AI models.

**Module Type:** 🚀 Entry Point

![Architecture](static/description/llm_assistant_architecture.png)

## Installation

### What to Install

This is the **main entry point** for AI chat features in Odoo.

**Basic AI Chat Setup:**

```bash
odoo-bin -d your_db -i llm_assistant,llm_openai
```

### Auto-Installed Dependencies

These are pulled in automatically:

- `llm` (core infrastructure)
- `llm_tool` (function calling)
- `llm_thread` (chat interface)
- `mail` (Odoo messaging)

### Choose a Provider

| Provider | Module        | Best For                    |
| -------- | ------------- | --------------------------- |
| OpenAI   | `llm_openai`  | GPT-4, most capable         |
| Ollama   | `llm_ollama`  | Local/private, no API costs |
| Mistral  | `llm_mistral` | European, fast              |

### Common Setups

| I want to...                    | Install                                                      |
| ------------------------------- | ------------------------------------------------------------ |
| Chat with GPT-4 in Odoo         | `llm_assistant` + `llm_openai`                               |
| Use local AI (privacy)          | `llm_assistant` + `llm_ollama`                               |
| Add document search (RAG)       | Above + `llm_knowledge` + `llm_pgvector`                     |
| Connect Claude Desktop          | Above + `llm_mcp_server`                                     |
| Build domain-specific assistant | Extend `llm_assistant` (see `llm_assistant_account_invoice`) |

## Overview

The LLM Assistant module provides sophisticated AI assistant management that goes far beyond simple chatbots. It serves as the intelligent configuration layer that orchestrates how AI models interact with Odoo data, with integrated prompt template management and comprehensive testing capabilities.

### Core Capabilities

- **AI Assistant Configuration** - Define specialized AI personas with specific roles and capabilities
- **Integrated Prompt Management** - Consolidated prompt template system (formerly separate `llm_prompt` module)
- **Template Testing** - Built-in testing wizard for prompt validation and optimization
- **Context Orchestration** - Intelligent mapping between Odoo data and AI inputs
- **Tool Management** - Configure available tools and their usage patterns
- **Generation Configuration** - Templates for different content types (text, images, etc.)

## Key Features

### Consolidated Architecture

The module consolidates functionality from the former `llm_prompt` module:

- ✅ **Prompt templates integrated** into assistant management
- ✅ **Enhanced testing wizard** with context simulation
- ✅ **Streamlined UI** with unified assistant and prompt selection
- ✅ **Auto-argument detection** for template variables
- ✅ **Schema synchronization** between templates and forms

### Assistant Types & Use Cases

#### 1. Chat Assistants

Configure conversational AI with specific personas:

```python
# Customer service assistant
assistant = env['llm.assistant'].create({
    'name': 'Customer Support Bot',
    'role': 'Customer Service Representative',
    'goal': 'Provide helpful and accurate customer support',
    'background': 'Expert in our products with access to CRM data',
    'instructions': '''
        - Always be polite and professional
        - Use customer history to provide personalized responses
        - Escalate complex issues to human agents
        - Provide clear, actionable solutions
    ''',
    'tool_ids': [(6, 0, [crm_tool.id, knowledge_tool.id])]
})
```

#### 2. Content Generation Assistants

Configure specialized content creation workflows:

```python
# Marketing content generator
assistant = env['llm.assistant'].create({
    'name': 'Marketing Content Creator',
    'role': 'Marketing Specialist',
    'goal': 'Create compelling marketing content from product data',
    'prompt_id': marketing_template.id,
    'default_values': {
        'brand_voice': 'professional yet approachable',
        'target_audience': 'business professionals'
    }
})
```

#### 3. Analysis Assistants

Configure data analysis and insights:

```python
# Business intelligence assistant
assistant = env['llm.assistant'].create({
    'name': 'BI Analyst',
    'role': 'Business Intelligence Analyst',
    'goal': 'Analyze business data and provide actionable insights',
    'tool_ids': [(6, 0, [reporting_tool.id, analytics_tool.id])]
})
```

### Integrated Prompt Template System

#### Template Management

```python
# Create prompt template with auto-detection
prompt = env['llm.prompt'].create({
    'name': 'Sales Email Generator',
    'template': '''
Generate a personalized sales email for {{customer_name}}
regarding {{product_name}}.

Customer Context:
- Company: {{customer_company}}
- Industry: {{industry}}
- Previous purchases: {{purchase_history}}

Email should be {{tone}} and focus on {{key_benefits}}.
    ''',
    'format': 'text',
    'category_id': sales_category.id
})

# Arguments automatically detected and schema generated
prompt.auto_detect_arguments()
```

#### Advanced Template Formats

**YAML Format** for structured conversations:

```yaml
messages:
  - type: system
    content: |
      You are {{role}}. Your goal is {{goal}}.
      Customer: {{customer_name}} ({{customer_company}})
  - type: user
    content: |
      {{user_request}}
```

**JSON Format** for direct API compatibility:

```json
{
  "messages": [
    {
      "type": "system",
      "content": "You are {{role}} helping {{customer_name}}"
    },
    {
      "type": "user",
      "content": "{{user_input}}"
    }
  ],
  "temperature": {{temperature}},
  "max_tokens": {{max_tokens}}
}
```

### Testing & Validation

#### Enhanced Testing Wizard

The integrated testing wizard provides comprehensive validation:

```python
# Launch testing wizard
wizard = env['llm.assistant.test.wizard'].create({
    'assistant_id': assistant.id,
    'test_context': {
        'customer_name': 'John Smith',
        'customer_company': 'Acme Corp',
        'product_name': 'Enterprise Software'
    }
})

# Test with different scenarios
wizard.run_test_scenarios([
    {'tone': 'professional', 'urgency': 'high'},
    {'tone': 'friendly', 'urgency': 'low'},
    {'tone': 'formal', 'urgency': 'medium'}
])
```

#### Auto-Detection Features

- **Template Arguments**: Automatically detect `{{variables}}` in templates
- **Schema Generation**: Create JSON schemas for form generation
- **Validation**: Ensure template-schema consistency
- **Default Values**: Smart defaults based on context

### Context Orchestration

#### Data Mapping Configuration

```python
def prepare_context(self, record=None, user_input=None):
    """Transform Odoo data into LLM-compatible context"""
    context = {}

    if record and record._name == 'sale.order':
        context.update({
            'customer_name': record.partner_id.name,
            'order_total': record.amount_total,
            'order_date': record.date_order,
            'sales_person': record.user_id.name
        })

    # Add user input and system context
    context['user_input'] = user_input
    context['current_date'] = fields.Date.today()

    return context
```

#### Intelligent History Management

```python
def trim_conversation_history(self, messages, max_tokens=4000):
    """Intelligent context window management"""
    # Keep system message and recent context
    # Remove older messages while preserving important context
    # Maintain conversation coherence
```

## Configuration Guide

### 1. Basic Assistant Setup

```python
# Create specialized assistant
assistant = env['llm.assistant'].create({
    'name': 'Sales Assistant',
    'role': 'Sales Representative',
    'goal': 'Help close deals and provide product information',
    'background': 'Expert in our product portfolio with CRM access',
    'instructions': '''
        Key behaviors:
        - Always qualify leads before pitching
        - Use customer data to personalize responses
        - Focus on value propositions
        - Suggest appropriate products based on needs
    ''',
    'provider_id': openai_provider.id,
    'model_id': gpt4_model.id,
    'tool_ids': [(6, 0, [crm_search.id, product_catalog.id])]
})
```

### 2. Prompt Template Integration

```python
# Create template for the assistant
template = env['llm.prompt'].create({
    'name': 'Sales Conversation Template',
    'template': '''
You are {{role}} working with {{customer_name}} from {{customer_company}}.

Customer Profile:
- Industry: {{industry}}
- Size: {{company_size}}
- Budget Range: {{budget_range}}
- Key Pain Points: {{pain_points}}

Your goal: {{goal}}

Guidelines: {{instructions}}
    ''',
    'arguments_json': {
        'customer_name': {'type': 'string', 'required': True},
        'customer_company': {'type': 'string', 'required': True},
        'industry': {'type': 'string', 'required': False},
        'budget_range': {'type': 'string', 'required': False}
    }
})

# Link template to assistant
assistant.prompt_id = template.id
```

### 3. Tool Configuration

```python
# Configure available tools for assistant
assistant.tool_ids = [(6, 0, [
    crm_search_tool.id,      # Search CRM records
    product_catalog_tool.id,  # Access product information
    pricing_tool.id,         # Get pricing and discounts
    calendar_tool.id,        # Schedule meetings
    email_tool.id           # Send follow-up emails
])]
```

## API Reference

### Assistant Methods

```python
# Get system prompt with context
system_prompt = assistant.get_system_prompt(context={
    'customer_name': 'John Doe',
    'customer_company': 'ABC Corp'
})

# Prepare conversation context
context = assistant.prepare_context(
    record=sale_order,
    user_input="Tell me about pricing options"
)

# Get available tools
tools = assistant.get_available_tools()

# Render prompt template
messages = assistant.prompt_id.get_messages(arguments={
    'customer_name': 'John Doe',
    'role': 'Sales Assistant'
})
```

### Template Methods

```python
# Auto-detect template arguments
prompt.auto_detect_arguments()

# Render template with arguments
rendered = prompt.get_messages(arguments={
    'customer_name': 'John Smith',
    'product_name': 'Enterprise Suite'
})

# Validate template syntax
is_valid, errors = prompt.validate_template()
```

## Integration Examples

### CRM Integration

```python
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def create_ai_assistant_thread(self):
        """Create AI assistant thread for this sale order"""
        thread = self.env['llm.thread'].create({
            'name': f'Sales Discussion - {self.name}',
            'model': self._name,
            'res_id': self.id,
            'assistant_id': self.env.ref('my_module.sales_assistant').id
        })

        # Initialize with order context
        context = {
            'customer_name': self.partner_id.name,
            'order_total': self.amount_total,
            'products': [line.product_id.name for line in self.order_line]
        }

        thread.message_post(
            body=f"AI Assistant ready to help with {self.name}",
            llm_role="system",
            body_json={'context': context}
        )

        return thread
```

### Project Management Integration

```python
class ProjectTask(models.Model):
    _inherit = 'project.task'

    def get_ai_assistance(self, query):
        """Get AI assistance for project tasks"""
        assistant = self.env.ref('my_module.project_assistant')

        context = assistant.prepare_context(
            record=self,
            user_input=query
        )

        # Generate AI response with project context
        response = assistant.generate_response(
            context=context,
            tools=['project_search', 'time_tracking', 'resource_planning']
        )

        return response
```

## Technical Specifications

### Module Information

- **Name**: LLM Assistant
- **Version**: 18.0.1.5.0
- **Category**: Productivity
- **License**: LGPL-3
- **Dependencies**: `llm`, `mail`
- **Author**: Apexive Solutions LLC

### Key Models

- **`llm.assistant`**: Main assistant configuration
- **`llm.prompt`**: Integrated prompt template management
- **`llm.prompt.category`**: Template categorization
- **`llm.assistant.test.wizard`**: Testing and validation

## Performance Features

- **Smart Context Management**: Intelligent conversation history trimming
- **Template Caching**: Optimized template rendering and argument detection
- **Async Operations**: Non-blocking testing and validation
- **Database Optimization**: Efficient storage of assistant configurations

## Security Features

- **Role-Based Access**: Control who can create and modify assistants
- **Tool Permissions**: Granular control over tool access per assistant
- **Template Validation**: Prevent execution of malicious templates
- **Audit Trail**: Complete tracking of assistant usage and modifications

## Related Modules

- **`llm`**: Base infrastructure and provider management
- **`llm_thread`**: Chat interfaces and conversation management
- **`llm_tool`**: Function calling and Odoo integration
- **`llm_generate`**: Content generation with assistant integration
- **`llm_knowledge`**: RAG and knowledge base integration

## Support & Resources

- **Documentation**: [GitHub Repository](https://github.com/apexive/odoo-llm)
- **Architecture Guide**: [OVERVIEW.md](../OVERVIEW.md)
- **Examples**: [Assistant Examples](examples/)
- **Community**: [GitHub Discussions](https://github.com/apexive/odoo-llm/discussions)

## License

This module is licensed under [LGPL-3](https://www.gnu.org/licenses/lgpl-3.0.html).

---

_© 2025 Apexive Solutions LLC. All rights reserved._
