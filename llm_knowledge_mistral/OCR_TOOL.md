# Mistral OCR Tool - llm_mistral_attachment_parser

## Overview

A simple, generic LLM tool that extracts text from PDF and image attachments using Mistral's OCR vision models. **Supports both single and batch processing** of multiple attachments.

## Implementation

**File**: `llm_knowledge_mistral/models/ir_attachment.py`

**Tool Name**: `llm_mistral_attachment_parser`

**Model**: `ir.attachment`

## What It Does

1. Takes `attachment_id` (single) or `attachment_ids` (batch) as input
2. Retrieves the attachment(s) from Odoo
3. Automatically finds the Mistral provider and OCR model
4. Processes the document(s) using `provider.process_ocr()`
5. Returns markdown-formatted text with page headers
6. **Batch mode**: Processes multiple attachments in one call with error handling per document

## Usage

### From LLM Assistant

**Single Attachment:**

```
User: "Parse attachment 123"
Assistant: [calls llm_mistral_attachment_parser(attachment_id=123)]
Assistant: "I extracted the following text: ..."
```

**Batch Processing:**

```
User: "Parse attachments 123, 124, and 125"
Assistant: [calls llm_mistral_attachment_parser(attachment_ids=[123, 124, 125])]
Assistant: "I parsed 3 documents:
- invoice.pdf (2 pages)
- receipt.jpg (1 page)
- contract.pdf (5 pages)"
```

### Programmatically

**Single Attachment:**

```python
result = env['ir.attachment'].llm_mistral_attachment_parser(attachment_id=123)

# Returns:
{
    "attachment_id": 123,
    "extracted_text": "## Page 1\n\nInvoice #12345...",
    "pages": 2,
    "attachment_name": "invoice.pdf",
    "mimetype": "application/pdf"
}
```

**Batch Processing:**

```python
results = env['ir.attachment'].llm_mistral_attachment_parser(
    attachment_ids=[123, 124, 125]
)

# Returns list:
[
    {
        "attachment_id": 123,
        "extracted_text": "## Page 1\n\nInvoice...",
        "pages": 2,
        "attachment_name": "invoice.pdf",
        "mimetype": "application/pdf"
    },
    {
        "attachment_id": 124,
        "extracted_text": "## Page 1\n\nReceipt...",
        "pages": 1,
        "attachment_name": "receipt.jpg",
        "mimetype": "image/jpeg"
    },
    {
        "attachment_id": 125,
        "error": "Attachment has no content",  # Failed attachment
        "extracted_text": "",
        "pages": 0
    }
]
```

**Error Handling:**

```python
# Raises exceptions for single mode:
# ValidationError: "Attachment with ID 123 not found"
# UserError: "Mistral provider not found. Please configure..."

# Batch mode: Returns errors per document in results array
# Does NOT stop on first error - processes all documents
```

## Return Format

**Single Attachment** (dict):

```python
{
    "attachment_id": int,      # Attachment ID
    "extracted_text": str,     # Markdown text with "## Page N" headers
    "pages": int,              # Number of pages processed
    "attachment_name": str,    # Original filename
    "mimetype": str,           # File MIME type
}
```

**Batch Processing** (list of dicts):

```python
[
    {
        "attachment_id": int,
        "extracted_text": str,
        "pages": int,
        "attachment_name": str,
        "mimetype": str
    },
    # ... more documents
    {
        "attachment_id": int,
        "error": str,          # Present if parsing failed
        "extracted_text": "",  # Empty on error
        "pages": 0            # Zero on error
    }
]
```

## Error Handling

**Single Mode**: Raises standard Odoo exceptions

- **`ValidationError`**: No attachment specified, not found, or has no content
- **`UserError`**: Mistral provider or OCR model not configured
- Other exceptions propagate naturally (e.g., API errors, network issues)

**Batch Mode**: Continues on error

- Does NOT raise exceptions
- Failed documents included in results with `"error"` field
- Successful documents have full parsed data
- All attachments attempted, even if some fail

## Batch Processing Benefits

✅ **Performance**: Parse multiple documents in one tool call
✅ **Resilience**: Continues processing even if some docs fail
✅ **Efficiency**: Reduce round-trips for multi-document workflows
✅ **Error Reporting**: See which docs succeeded/failed in one response
✅ **Use Cases**:

- Parse all invoice attachments at once
- Process multiple receipts from expense report
- Extract data from multi-file submissions
- Batch document analysis workflows

## Requirements

1. **Mistral Provider**: Must be configured in LLM settings
2. **OCR Model**: At least one OCR model must be synced (e.g., "pixtral-12b-2409")
3. **Attachment**: Must have content (datas field not empty)

## Supported File Types

- PDF documents (`application/pdf`)
- Images (JPEG, PNG, etc.)
- Any file type that Mistral OCR supports

## How It Works

### 1. Automatic Model Selection (Smart Priority)

The tool automatically selects the best available OCR model with this priority:

**Priority 1**: `mistral-ocr-latest` with `model_use = "ocr"`

```python
ocr_model = env["llm.model"].search([
    ("provider_id", "=", provider.id),
    ("name", "=", "mistral-ocr-latest"),
    ("model_use", "=", "ocr")
], limit=1)
```

**Priority 2**: Any model named `mistral-ocr-latest` (regardless of model_use)

```python
if not ocr_model:
    ocr_model = env["llm.model"].search([
        ("provider_id", "=", provider.id),
        ("name", "=", "mistral-ocr-latest")
    ], limit=1)
```

**Priority 3**: Any model with `model_use = "ocr"`

```python
if not ocr_model:
    ocr_model = env["llm.model"].search([
        ("provider_id", "=", provider.id),
        ("model_use", "=", "ocr")
    ], limit=1)
```

This ensures the tool prefers the latest stable OCR model while gracefully falling back to alternatives.

### 2. Document Processing

```python
# Decode attachment data
data_bytes = base64.b64decode(attachment.datas)

# Call Mistral OCR
ocr_response = provider.process_ocr(
    model_name=ocr_model.name,
    data=data_bytes,
    mimetype=attachment.mimetype
)
```

### 3. Response Formatting

```python
# Simple markdown formatting
for page_idx, page in enumerate(ocr_response.pages, start=1):
    parts.append(f"## Page {page_idx}\n\n{page.markdown}")

return "\n\n".join(parts)
```

## Exception Handling

The tool uses standard Odoo exception patterns for clean error handling:

```python
from odoo.exceptions import UserError, ValidationError

# ValidationError for data issues
if not attachment.exists():
    raise ValidationError(f"Attachment with ID {attachment_id} not found")

# UserError for configuration issues
if not provider:
    raise UserError("Mistral provider not found. Please configure...")

# Other exceptions propagate naturally
# The LLM system will catch and present them to the user
```

## Differences from llm.resource Parser

| Feature             | llm.resource (mistral_ocr)                 | This Tool (llm_mistral_attachment_parser) |
| ------------------- | ------------------------------------------ | ----------------------------------------- |
| Purpose             | Parse resource content into knowledge base | Parse any attachment on-demand            |
| Creates attachments | Yes (for extracted images)                 | No                                        |
| Stores result       | Yes (in self.content)                      | No (returns directly)                     |
| Image handling      | Re-encodes and stores images               | Ignores images (text only)                |
| Use case            | Knowledge base ingestion                   | LLM tool for assistants                   |

## Integration with llm_invoice_assistant

Once this tool is registered, it can be used by the Invoice Analysis Assistant:

```xml
<record id="llm_assistant_invoice_analyzer" model="llm.assistant">
    <field
    name="tool_ids"
    eval="[(6, 0, [
        ref('llm_knowledge_mistral.llm_tool_llm_mistral_attachment_parser'),
        ref('llm_tool.llm_tool_odoo_record_retriever'),
        ...
    ])]"
  />
</record>
```

## Tool Registration

The tool is **automatically registered** via the `@llm_tool` decorator:

1. On module install/upgrade
2. `llm.tool._register_hook()` scans all models
3. Finds methods with `_is_llm_tool` attribute
4. Creates/updates `llm.tool` record

**No XML data file needed!**

## Testing

### Manual Test

1. Install/upgrade module: `odoo-bin -d mydb -u llm_knowledge_mistral`
2. Upload a PDF to any record
3. Create an LLM thread
4. Ask: "Parse document from attachment [ID]"
5. Verify: Tool extracts text correctly

### Programmatic Test

```python
# In Odoo shell or test
attachment = env['ir.attachment'].create({
    'name': 'test.pdf',
    'datas': base64.b64encode(pdf_bytes),
    'mimetype': 'application/pdf'
})

result = env['ir.attachment'].llm_mistral_attachment_parser(attachment.id)
assert 'extracted_text' in result
assert result['pages'] > 0
```

## Future Enhancements

1. **Image extraction option**: Add parameter to return images as attachments
2. **Page selection**: Allow parsing specific pages only
3. **Language hint**: Pass language hint to OCR for better accuracy
4. **Structured extraction**: Add JSON schema parameter for structured output

## Notes

- **Generic by design**: Works with ANY attachment, not just invoices
- **Reusable**: Can be used by any assistant or workflow
- **Simple**: No chunking, no vector storage, just parsing
- **Stateless**: Doesn't modify any data, just returns results
