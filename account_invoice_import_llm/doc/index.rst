===============================
Account Invoice Import LLM
===============================

AI-powered invoice data extraction with OCR for Odoo 18 - integrates with OCA's account_invoice_import.

Features
========

- **Automatic OCR Extraction**: Extract invoice data from PDFs and images using Mistral OCR
- **One-Shot AI Processing**: Single LLM call extracts all invoice data (vendor, dates, amounts, line items)
- **OCA Integration**: Seamlessly extends ``account_invoice_import`` wizard as fallback parser
- **Manual Trigger**: "Process with AI" button for on-demand extraction
- **Smart Data Mapping**: Converts LLM output to OCA's Invoice Pivot Format

Installation
============

1. Install dependencies:

   - ``account_invoice_import`` (OCA - invoice import wizard)
   - ``llm_assistant`` (LLM infrastructure)
   - ``llm_mistral`` (Mistral provider for OCR)

2. Install the module:

   .. code-block:: bash

      odoo-bin -d your_database -i account_invoice_import_llm

3. Configure Mistral provider in **Settings → LLM → Providers** (for OCR)

4. Configure the Invoice Extraction Assistant:

   - Go to **Settings → LLM → Assistants**
   - Open **"Invoice Data Extraction (Automatic)"**
   - Select a **Provider** (e.g., OpenAI, Anthropic, Google)
   - Select a **Model** (e.g., gpt-4o, claude-3-sonnet, gemini-pro)
   - Save

Usage
=====

Two Ways to Extract Invoice Data
---------------------------------

1. **Manual Processing**

   For invoices with attached PDF/image:

   - Open a draft invoice with an attached PDF/image
   - Click **"Process with AI"** button
   - **Form reloads with extracted data**

2. **OCA Invoice Import Wizard**

   When using OCA's invoice import wizard:

   - Go to **Accounting → Vendors → Import Vendor Bill**
   - Upload PDF invoice
   - If no embedded XML found, **LLM extraction is used as fallback**
   - Invoice is created with extracted data

What Gets Extracted
-------------------

The LLM extracts and populates:

- Vendor name and VAT number
- Invoice number and reference
- Invoice date and due date
- Currency
- Subtotal, tax, and total amounts
- Line items with descriptions, quantities, unit prices, and tax rates

Module Architecture
===================

OCA Invoice Import Integration
-------------------------------

Follows the standard OCA pattern for extending ``account_invoice_import``::

   account_invoice_import_llm/
   ├── __manifest__.py                   # Dependencies and metadata
   ├── __init__.py                       # Pre-init hook for module rename
   ├── models/
   │   ├── account_invoice_import_ocr.py # AbstractModel: OCR + LLM extraction
   │   └── account_move.py               # "Process with AI" button
   ├── wizard/
   │   └── account_invoice_import.py     # OCA fallback_parse_pdf_invoice()
   ├── data/
   │   ├── llm_prompt_invoice_data.xml   # One-shot extraction prompt
   │   └── llm_assistant_data.xml        # Assistant configuration
   └── views/
       └── account_move_views.xml        # Button view extension

Processing Flows
----------------

Flow 1: Manual Trigger::

   1. User clicks "Process with AI" button
      ↓
   2. action_process_with_llm()
      - Validates invoice is draft
      - Finds PDF/image attachment
      ↓
   3. extract_invoice_data()
      - Runs OCR on file bytes
      - Renders prompt with OCR text
      - Calls LLM for extraction
      ↓
   4. _update_invoice_from_pivot()
      - Converts to OCA pivot format
      - Updates invoice fields
      ↓
   5. Returns action to reload form view
      ↓
   6. User sees populated invoice data

Flow 2: OCA Wizard Fallback::

   1. User uploads PDF via OCA wizard
      ↓
   2. Wizard calls parse_pdf_invoice()
      ↓
   3. Checks for embedded XML (UBL, Factur-X)
      - If found: Uses XML parser
      - If not found: Calls fallback_parse_pdf_invoice()
      ↓
   4. Our fallback_parse_pdf_invoice()
      - Extracts data via LLM
      - Converts to OCA's Invoice Pivot Format
      ↓
   5. Wizard creates invoice from pivot format

Key Components
--------------

1. **OCR Extraction AbstractModel**

   **File**: ``models/account_invoice_import_ocr.py``

   Central extraction logic shared by wizard and manual button:

   - Runs Mistral OCR on file bytes
   - Renders prompt with OCR text context
   - Calls LLM for structured extraction
   - Converts to OCA Invoice Pivot Format

2. **One-Shot Extraction Prompt**

   **File**: ``data/llm_prompt_invoice_data.xml``

   Structured prompt that instructs LLM to extract invoice data in JSON format.

3. **OCA Wizard Integration**

   **File**: ``wizard/account_invoice_import.py``

   Extends ``fallback_parse_pdf_invoice()`` to delegate to OCR AbstractModel.

Technical Details
=================

Error Handling Strategy
------------------------

- **Wizard flow**: Catches exceptions and returns ``res`` gracefully (doesn't break OCA flow)
- **Manual button**: Lets exceptions propagate as UserError with helpful messages
- **Logging**: Detailed error info in server logs for debugging

Pre-Init Hook
-------------

**File**: ``__init__.py``

Handles module rename from ``llm_assistant_account_invoice`` → ``account_invoice_import_llm``:

1. Updates ``ir_model_data`` records from old module name
2. Adopts orphaned records (prevents FK violations)
3. Prevents duplicate key errors on installation

Configuration
=============

Invoice Extraction Assistant
-----------------------------

**Location**: Settings → LLM → Assistants → Invoice Data Extraction (Automatic)

The assistant is pre-configured with:

- **Prompt**: One-shot extraction template with detailed instructions
- **Model**: Any LLM (GPT-4, Claude, Gemini, etc.)
- **OCR Tool**: Mistral OCR for text extraction
- **Dynamic Context**: OCR text injected automatically

Customization
-------------

To customize extraction behavior:

1. Go to **Settings → LLM → Prompts → Invoice Data Extraction (One-Shot)**
2. Edit the ``instructions`` argument to add/remove fields
3. Update the JSON structure in ``default_values``
4. Modify ``_convert_llm_data_to_pivot()`` if adding new fields

Troubleshooting
===============

Issue: "No PDF or image attachment found"
------------------------------------------

**Solution**: Attach a PDF or image file to the invoice before clicking "Process with AI"

Issue: "Failed to extract data"
--------------------------------

**Possible causes**:

- Poor quality scan/image
- Non-standard invoice format
- OCR couldn't extract text

**Solution**: Check server logs for detailed error. Try with a higher quality scan.

Issue: "Mistral provider not configured"
-----------------------------------------

**Solution**: Install ``llm_mistral`` module and configure Mistral provider with API key

Issue: Duplicate records after module rename
---------------------------------------------

**Solution**: The pre-init hook should handle this automatically. If issues persist, check ``ir_model_data`` for orphaned records.

Credits
=======

Authors
-------

- Apexive Solutions LLC

Maintainers
-----------

This module is maintained by Apexive Solutions LLC.

License
=======

LGPL-3
