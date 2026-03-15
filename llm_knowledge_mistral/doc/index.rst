===========================
LLM Knowledge Mistral
===========================

**Turn images into searchable knowledge** with Mistral AI's vision models.

**Module Type:** 🔌 Extension (OCR for Knowledge)

Architecture
============

::

    ┌───────────────────────────────────────────────────────────────┐
    │                      Image Sources                            │
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │
    │  │  Receipts   │  │ Handwritten │  │   Scanned Docs      │   │
    │  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘   │
    └─────────┼────────────────┼────────────────────┼──────────────┘
              └────────────────┼────────────────────┘
                               ▼
                  ┌───────────────────────────────────────────┐
                  │  ★ llm_knowledge_mistral (This Module) ★  │
                  │         Mistral OCR Parser                │
                  │  👁️ Vision │ 📝 Text Extract │ 🔍 Index   │
                  └─────────────────────┬─────────────────────┘
                                        │
                            ┌───────────┴───────────┐
                            ▼                       ▼
        ┌───────────────────────────┐   ┌───────────────────────────┐
        │       llm_knowledge       │   │        llm_mistral        │
        │      (RAG Pipeline)       │   │    (Mistral Provider)     │
        └───────────────────────────┘   └───────────────────────────┘

Installation
============

What to Install
---------------

**For image OCR in knowledge base:**

.. code-block:: bash

    odoo-bin -d your_db -i llm_knowledge_mistral

Auto-Installed Dependencies
---------------------------

- ``llm`` (core infrastructure)
- ``llm_knowledge`` (RAG infrastructure)
- ``llm_mistral`` (Mistral AI provider)

Why Use This Module?
--------------------

+------------------+-----------------------------+
| Feature          | llm_knowledge_mistral       |
+==================+=============================+
| **OCR**          | 👁️ Mistral vision models    |
+------------------+-----------------------------+
| **Handwriting**  | ✍️ Handwritten text support |
+------------------+-----------------------------+
| **Multi-format** | 📄 PDF, PNG, JPG, WEBP      |
+------------------+-----------------------------+
| **Searchable**   | 🔍 Images become searchable |
+------------------+-----------------------------+

Common Setups
-------------

+------------------+-----------------------------------------------------------------------+
| I want to...     | Install                                                               |
+==================+=======================================================================+
| OCR + RAG        | ``llm_knowledge_mistral`` + ``llm_pgvector``                          |
+------------------+-----------------------------------------------------------------------+
| Chat + OCR + RAG | ``llm_assistant`` + ``llm_openai`` + ``llm_knowledge_mistral`` +      |
|                  | ``llm_pgvector``                                                      |
+------------------+-----------------------------------------------------------------------+

Extract text from handwritten notes, receipts, scanned documents, screenshots, and product labels. Make every image searchable in your knowledge base with automatic OCR processing.

Overview
========

This module extends ``llm_knowledge`` with Mistral AI's vision capabilities, enabling OCR (Optical Character Recognition) for images and scanned documents. Upload an image, and Mistral's vision models extract all text content, making it fully searchable through your AI assistant.

The Problem
-----------

Without OCR:

- Images are just binary blobs in your knowledge base
- Handwritten notes can't be searched
- Scanned documents are dead weight
- Receipts and invoices are unusable
- Knowledge stays locked in images

The Solution
------------

With Mistral OCR:

- AI extracts text from any image
- Handwriting becomes searchable
- Scanned docs fully indexed
- Receipt data automatically parsed
- Everything is findable

Features
========

Mistral Vision OCR
------------------

- **State-of-the-art accuracy**: Powered by Mistral's multimodal vision models
- **Handwriting recognition**: Extracts text from handwritten notes and forms
- **Multi-format support**: Images (PNG, JPG, WEBP), PDFs, scanned documents
- **Automatic extraction**: No manual data entry required

OCR Models
----------

Three Mistral OCR models available:

- **mistral-ocr-latest**: Latest OCR model (recommended)
- **mistral-ocr-2505**: May 2025 version
- **mistral-ocr-2503**: March 2025 version

Mistral OCR Parser
------------------

- Seamless integration with llm_knowledge processing pipeline
- Automatic text extraction from image attachments
- Preserves original images while extracting text content
- Works with existing chunking and embedding systems

Installation
============

1. **Install dependencies**:

   - ``llm_knowledge`` module (required)
   - ``llm_mistral`` module (required)

2. **Install this module**:

   .. code-block:: bash

      # Via Odoo Apps interface
      Apps → Search "LLM Knowledge Mistral" → Install

3. **Set up Mistral provider**:

   - Go to **LLM → Configuration → Providers**
   - Configure your Mistral AI provider with API key
   - Click "Fetch Models" to download available OCR models from Mistral
   - This populates the OCR models list automatically

Configuration
=============

Step 1: View OCR Models
------------------------

The module comes pre-configured with Mistral's OCR models. View them under **LLM → Configuration → Models**, filtered by "ocr".

.. image:: ../static/description/screenshots/mistral_ocr_models.png
   :alt: Mistral OCR Models

**Available models**:

- ``mistral-ocr-latest`` - Latest OCR model (recommended)
- ``mistral-ocr-2505`` - May 2025 version
- ``mistral-ocr-2503`` - March 2025 version

Step 2: Configure Parser
-------------------------

When creating or editing a knowledge resource:

1. Select **"Mistral OCR Parser"** from the Parser dropdown
2. Choose your preferred OCR model (mistral-ocr-latest recommended)
3. Upload images as attachments
4. Click "Process Resources"

.. image:: ../static/description/screenshots/mistral_parser.png
   :alt: Mistral Parser Configuration

**Parser settings**:

- **Parser**: Mistral OCR Parser
- **Provider**: Mistral AI (auto-selected)
- **OCR Model**: mistral-ocr-latest or specific version
- **Supported formats**: PNG, JPG, WEBP, PDF

Step 3: Process and Search
---------------------------

Click "Process Resources" to extract text from your images. The extracted text becomes searchable through your AI assistant.

Usage Examples
==============

Handwritten Grocery List
-------------------------

**Input**: Photo of handwritten grocery list

.. image:: ../static/description/screenshots/grocerylist.webp
   :alt: Handwritten Grocery List

**Output**: Extracted text

.. code-block:: text

   - potatoes
   - peas & carrots
   - pastina
   - garbage bags
   - dog treats
   - aluminum foil
   - almond milk
   - creamer - vanilla
   - eggs (2)
   - crushed tomatoes
   - hot sauce
   - paper towels?

**Result**: Fully searchable in knowledge base. Ask "What items are on the grocery list?" and AI finds and lists all items.

Expense Management
------------------

**Goal**: Track business expenses from receipt photos

**Setup**:

- Upload receipt photos to knowledge collection
- Use Mistral OCR Parser
- Process resources

**Result**: Extract vendor, amount, date, and items from receipts. Search "Find all Starbucks receipts from last month" → AI finds all matching receipts and totals.

Meeting Notes Archive
---------------------

**Goal**: Make handwritten meeting notes searchable

**Setup**:

- Scan or photograph handwritten meeting notes
- Upload to knowledge base
- Process with Mistral OCR

**Result**: Every decision, action item, and idea becomes searchable. Ask "What did we decide about the Q4 budget?" → AI cites exact meeting notes.

Product Label Extraction
------------------------

**Goal**: Index product information from label photos

**Setup**:

- Photograph product labels
- Add to product knowledge collection
- Process with Mistral OCR

**Result**: Extract ingredients, nutritional info, warnings, and instructions. AI can answer product questions using label data.

How It Works
============

Processing Pipeline
-------------------

When you process an image resource with Mistral OCR:

1. **Upload**: Attach image to llm.resource
2. **Parse**: Mistral OCR Parser sends image to Mistral AI vision model
3. **Extract**: Vision model analyzes image and extracts all text
4. **Save**: Extracted text saved to resource's content field
5. **Chunk**: Text chunked using collection's chunker settings
6. **Embed**: Chunks embedded and stored in vector database
7. **Search**: AI can now search and cite this content in responses

Supported Image Types
---------------------

- **Handwritten text**: Notes, forms, letters
- **Printed text**: Documents, books, manuals
- **Receipts**: Business expenses, invoices
- **Screenshots**: Error messages, UI text
- **Product labels**: Ingredients, instructions
- **Whiteboards**: Brainstorming sessions, diagrams
- **Forms**: Filled-out applications, surveys
- **Scanned documents**: PDFs, legacy files

Technical Details
=================

Mistral OCR Models
------------------

The available OCR models are fetched from Mistral AI when you configure the provider:

.. list-table::
   :header-rows: 1
   :widths: 30 40 30

   * - Model
     - Description
     - Recommended
   * - ``mistral-ocr-latest``
     - Latest OCR model
     - ✓ Yes
   * - ``mistral-ocr-2505``
     - May 2025 version
     - \-
   * - ``mistral-ocr-2503``
     - March 2025 version
     - \-

**Note**: You must set up the Mistral provider via ``llm_mistral`` module and click "Fetch Models" to download the available OCR models from Mistral AI.

Parser Registration
-------------------

The Mistral OCR Parser is registered in ``models/mistral_resource_parser.py`` on the ``llm.resource`` model:

.. code-block:: python

   @api.model
   def _get_available_parsers(self):
       parsers = super()._get_available_parsers()
       parsers.extend([
           ("mistral_ocr", "Mistral OCR Parser"),
       ])
       return parsers

The parser method ``parse_mistral_ocr()`` processes images:

.. code-block:: python

   def parse_mistral_ocr(self, record, field):
       mimetype = field["mimetype"]
       if not self.llm_model_id or not self.llm_provider_id:
           raise ValueError("Please select a model and provider.")
       value = field["rawcontent"]
       ocr_response = self.llm_provider_id.process_ocr(
           self.llm_model_id.name, value, mimetype
       )
       final_content = self._format_mistral_ocr_text(ocr_response, record.id)
       self.content = final_content
       return True

Fields Added to llm.resource
-----------------------------

This module extends ``llm.resource`` with:

- **llm_model_id**: Many2one to OCR model (domain: ``model_use = 'ocr'``)
- **llm_provider_id**: Many2one to Mistral provider (domain: ``service = 'mistral'``)

Troubleshooting
===============

OCR not extracting text
------------------------

1. Verify image quality is sufficient (not too blurry)
2. Check Mistral API credentials are configured
3. Review system logs for API errors
4. Try different OCR model version

Handwriting not recognized
---------------------------

1. Ensure handwriting is legible
2. Use high-resolution images
3. Try mistral-ocr-latest (best for handwriting)
4. Avoid low-light or skewed photos

Wrong text extracted
--------------------

1. Check image orientation (rotate if needed)
2. Verify image is not corrupted
3. Ensure sufficient contrast between text and background
4. Try cropping to focus on text area

Best Practices
==============

1. **Image quality**: Use high-resolution images (at least 1024px width)
2. **Lighting**: Ensure good lighting and contrast
3. **Orientation**: Rotate images to correct orientation before upload
4. **File format**: Use PNG or JPG for best results
5. **File size**: Keep images under 10MB for faster processing
6. **Batch processing**: Process multiple images at once for efficiency

Requirements
============

- **Odoo**: 18.0+
- **Python**: 3.11+
- **Dependencies**:

  - ``llm_knowledge`` module
  - ``llm_mistral`` module

- **API**: Mistral AI API key required

License
=======

LGPL-3

Author
======

**Apexive Solutions LLC**

- Website: https://github.com/apexive/odoo-llm
- Email: info@apexive.com

Contributing
============

Issues and pull requests welcome at https://github.com/apexive/odoo-llm
