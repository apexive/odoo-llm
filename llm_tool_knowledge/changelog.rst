18.0.1.0.1 (2025-10-23)
------------------------

* [MIG] Migrated to Odoo 18.0
* [FIX] Fixed tool schema generation to safely handle missing description keys
* [IMP] Updated view_mode references from 'tree' to 'list' for Odoo 18.0 compatibility

16.0.1.0.1 (2025-04-04)
------------------------

* [ADD] Added Knowledge Bot assistant that uses knowledge_retriever tool
* [IMP] Integrated with OpenAI GPT-4o model for enhanced knowledge retrieval capabilities

16.0.1.0.0 (2025-03-28)
------------------------

* Initial release of the LLM Tool RAG module
* Added Knowledge Retriever tool for semantic document search
* Implemented document search mixin for reusable search functionality
* Added integration with core RAG module for document chunk access
* Implemented security model with read-only access for regular users and full access for LLM managers
