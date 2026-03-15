18.0.1.2.0 (2025-11-28)
~~~~~~~~~~~~~~~~~~~~~~~

* [ADD] Added ollama_normalize_prepend_messages() to convert OpenAI list format to plain strings
* [FIX] Fixed Ollama compatibility with system prompts that use OpenAI's list content format
* [IMP] Changed ollama_chat to use generic format_messages() and format_tools() dispatch methods
* [IMP] Improved consistency with base provider dispatch pattern

18.0.1.1.0 (2025-10-23)
~~~~~~~~~~~~~~~~~~~~~~~

* [MIGRATION] Migrated to Odoo 18.0

16.0.1.1.0 (2025-03-06)
~~~~~~~~~~~~~~~~~~~~~~~

* [ADD] Updated chat method to accept additional params

16.0.1.0.0 (2025-01-02)
~~~~~~~~~~~~~~~~~~~~~~~

* [INIT] Initial release of the module
