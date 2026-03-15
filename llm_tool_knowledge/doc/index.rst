====================
LLM Tool Knowledge
====================

**Give your AI assistants instant access to your knowledge base** with semantic search and source citation capabilities.

**Module Type:** 🔌 Extension (RAG Tool)

Architecture
============

::

    ┌───────────────────────────────────────────────────────────────┐
    │                    AI Consumers                               │
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │
    │  │llm_assistant│  │  llm_letta  │  │   llm_mcp_server    │   │
    │  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘   │
    └─────────┼────────────────┼────────────────────┼──────────────┘
              └────────────────┼────────────────────┘
                               ▼
                  ┌───────────────────────────────────────────┐
                  │    ★ llm_tool_knowledge (This Module) ★   │
                  │         Knowledge Retriever Tool          │
                  │  🔍 Semantic Search │ 📚 Source Citations │
                  └─────────────────────┬─────────────────────┘
                                        │
                            ┌───────────┴───────────┐
                            ▼                       ▼
        ┌───────────────────────────┐   ┌───────────────────────────┐
        │         llm_tool          │   │       llm_knowledge       │
        │    (Tool Framework)       │   │      (RAG Pipeline)       │
        └───────────────────────────┘   └───────────────────────────┘

Installation
============

What to Install
---------------

**For RAG tool access:**

.. code-block:: bash

    odoo-bin -d your_db -i llm_tool_knowledge

Auto-Installed Dependencies
---------------------------

- ``llm`` (core infrastructure)
- ``llm_tool`` (tool framework)
- ``llm_knowledge`` (RAG infrastructure)
- ``llm_assistant`` (AI assistant framework)

Why Use This Module?
--------------------

+---------------+----------------------------------+
| Feature       | llm_tool_knowledge               |
+===============+==================================+
| **Search**    | 🔍 Semantic similarity search    |
+---------------+----------------------------------+
| **Citations** | 📚 Source document references    |
+---------------+----------------------------------+
| **Hybrid**    | 🔄 Semantic + keyword search     |
+---------------+----------------------------------+
| **Dual Use**  | 🤖 Odoo assistants + MCP clients |
+---------------+----------------------------------+

Common Setups
-------------

+----------------+------------------------------------------------------------------------+
| I want to...   | Install                                                                |
+================+========================================================================+
| Chat + RAG     | ``llm_assistant`` + ``llm_openai`` + ``llm_tool_knowledge`` +          |
|                | ``llm_pgvector``                                                       |
+----------------+------------------------------------------------------------------------+
| Claude + RAG   | ``llm_mcp_server`` + ``llm_tool_knowledge`` + ``llm_pgvector``         |
+----------------+------------------------------------------------------------------------+

This module provides RAG (Retrieval-Augmented Generation) tools that enable AI assistants to search documents, cite sources, and answer questions using your actual company data instead of just their training.

Overview
========

LLM Tool Knowledge extends the Odoo LLM ecosystem with a powerful ``knowledge_retriever`` tool that performs semantic search across your knowledge collections. This tool can be used in two ways:

1. **With Odoo AI Assistants** (``llm_assistant`` module) - Enable your internal Odoo chatbots to search company knowledge
2. **With External MCP Clients** (``llm_mcp_server`` module) - Expose your knowledge base to external AI tools like Claude Desktop, Continue.dev, and other MCP-compatible applications

Features
========

Knowledge Retriever Tool
------------------------

- **Semantic Search**: Find relevant documents using natural language queries
- **Source Citations**: AI responses include references to source documents
- **Hybrid Search**: Combine semantic and keyword search for better accuracy
- **Collection-Aware**: Search specific collections or across all knowledge
- **Configurable Relevance**: Set minimum similarity thresholds

Dual Integration
----------------

Odoo AI Assistants (llm_assistant)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When enabled on an assistant, the AI can automatically search your knowledge base:

.. code-block:: text

   User: "What's our refund policy?"
   AI: Uses knowledge_retriever tool → searches policy documents → cites sources

External MCP Clients (llm_mcp_server)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Expose the knowledge_retriever tool via Model Context Protocol:

.. code-block:: text

   Claude Desktop → MCP Server (Odoo) → knowledge_retriever → returns relevant docs

External AI tools can search your Odoo knowledge base securely.

Installation
============

1. **Install dependencies**:

   - ``llm_knowledge`` module (required)
   - ``llm_tool`` module (required)
   - ``llm_assistant`` module (required)
   - ``llm_mcp_server`` module (optional - for external MCP clients)

2. **Install this module**:

   .. code-block:: bash

      # Via Odoo Apps interface
      Apps → Search "LLM Tool Knowledge" → Install

3. **The tool is automatically registered** and ready to use.

Configuration
=============

For Odoo AI Assistants
-----------------------

1. Go to **LLM → Assistants → Assistants**
2. Open or create an assistant
3. Navigate to the **Tools** tab
4. Enable the "knowledge_retriever" tool
5. The assistant can now search knowledge collections

For External MCP Clients
-------------------------

1. Install and configure ``llm_mcp_server`` module
2. The ``knowledge_retriever`` tool is automatically exposed via MCP
3. Configure your MCP client (Claude Desktop, etc.) to connect to Odoo
4. External AI can now search your knowledge base

Usage Examples
==============

Example 1: Odoo Assistant with Knowledge Access
------------------------------------------------

**Setup**:

- Create knowledge collection with company policies
- Enable knowledge_retriever tool on support assistant

**Result**:

.. code-block:: text

   User: "What's the warranty period for laptops?"
   Assistant: [Searches policies collection]
   "Based on our Electronics Warranty Policy, laptops have a 2-year warranty covering
   hardware defects. (Source: Electronics Warranty Policy, updated Jan 2024)"

Example 2: Claude Desktop Accessing Odoo Knowledge
---------------------------------------------------

**Setup**:

- Configure llm_mcp_server with your Odoo instance
- Add server to Claude Desktop MCP settings
- Index product documentation in Odoo knowledge

**Result**:

.. code-block:: text

   Claude Desktop → uses knowledge_retriever tool → searches Odoo docs
   Returns: Relevant product specs with source citations from your knowledge base

Example 3: Continue.dev with Company Codebase
----------------------------------------------

**Setup**:

- Index code documentation in Odoo knowledge collection
- Expose via MCP server
- Configure Continue.dev to use Odoo MCP server

**Result**:

Developer asks Continue.dev about internal APIs → searches indexed docs → provides accurate answers from your actual documentation.

How It Works
============

Tool Input Schema
-----------------

.. code-block:: json

   {
     "type": "object",
     "properties": {
       "query": {
         "type": "string",
         "description": "Search query to find relevant knowledge"
       },
       "collection_id": {
         "type": "string",
         "description": "ID of knowledge collection to search (optional)"
       },
       "top_k": {
         "type": "integer",
         "description": "Number of results to return (default: 5)"
       },
       "min_similarity": {
         "type": "number",
         "description": "Minimum similarity score 0-1 (default: 0.7)"
       }
     },
     "required": ["query"]
   }

Tool Execution Flow
-------------------

1. **Receive query**: AI assistant or external tool calls knowledge_retriever
2. **Vector search**: Query is embedded and searched against knowledge chunks
3. **Filter results**: Apply similarity threshold and top_k limit
4. **Return sources**: Chunks with metadata, similarity scores, and source references
5. **AI uses context**: Assistant incorporates results into response with citations

Technical Details
=================

Tool Registration
-----------------

Defined in ``data/llm_tool_data.xml``:

.. code-block:: xml

   <record id="llm_tool_knowledge_retriever" model="llm.tool">
       <field name="name">knowledge_retriever</field>
       <field name="description">Retrieves relevant knowledge from document database
       using semantic search...</field>
       <field name="implementation">knowledge_retriever</field>
       <field name="active" eval="True" />
   </record>

Implementation
--------------

Located in ``models/llm_tool_knowledge_retriever.py``:

.. code-block:: python

   class LLMToolKnowledgeRetriever(models.Model):
       _inherit = "llm.tool"

       @api.model
       def _get_available_implementations(self):
           implementations = super()._get_available_implementations()
           return implementations + [("knowledge_retriever", "Knowledge Retriever")]

Search Process
--------------

1. Embed query using collection's embedding model
2. Perform vector similarity search in vector store (pgvector/Qdrant/Chroma)
3. Filter by min_similarity threshold
4. Return top_k most relevant chunks
5. Include source document metadata

Use Cases
=========

Internal Odoo Assistants
-------------------------

- **Customer Support**: Search FAQ, policies, product docs
- **HR Assistant**: Search employee handbook, HR policies
- **Sales Assistant**: Search product specs, pricing, competitor analysis
- **IT Helpdesk**: Search technical documentation, troubleshooting guides

External MCP Integration
-------------------------

- **Developer Tools**: Continue.dev, Cursor accessing code documentation
- **Claude Desktop**: Personal assistant with access to company knowledge
- **Custom AI Apps**: Build external apps that query Odoo knowledge
- **Multi-Tool Workflows**: Chain knowledge search with other MCP tools

Security
========

Access Control
--------------

- **Tool**: Requires ``llm.group_llm_user`` to execute
- **Collections**: Respects Odoo record rules and access rights
- **MCP Server**: Separate authentication for external access

Data Privacy
------------

- Knowledge searches respect user permissions
- External MCP access requires explicit configuration
- No knowledge is shared unless explicitly indexed in collections

Best Practices
==============

1. **Organize Collections**: Create topic-specific collections for better search accuracy
2. **Update Regularly**: Keep knowledge collections current with latest information
3. **Set Thresholds**: Adjust min_similarity based on precision/recall needs
4. **Limit Scope**: Use collection_id parameter to search specific domains
5. **Monitor Usage**: Track which queries are most common to improve indexing

Troubleshooting
===============

Tool not appearing
------------------

1. Verify module is installed and active
2. Check llm_knowledge module is installed
3. Refresh assistants or MCP client

Search returns no results
-------------------------

1. Check collection has processed resources (state=ready)
2. Verify embeddings are generated
3. Lower min_similarity threshold
4. Check vector store is configured correctly

MCP connection fails
--------------------

1. Verify llm_mcp_server is installed and configured
2. Check MCP client configuration matches Odoo URL
3. Review authentication credentials
4. Check Odoo is accessible from MCP client network

Requirements
============

- **Odoo**: 18.0+
- **Python**: 3.11+
- **Dependencies**:

  - ``llm_knowledge`` module (semantic search, vector storage)
  - ``llm_tool`` module (tool framework)
  - ``llm_assistant`` module (AI assistants)
  - ``llm_mcp_server`` module (optional - for external MCP clients)

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
