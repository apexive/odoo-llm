18.0.1.4.0 (2026-01-17)
~~~~~~~~~~~~~~~~~~~~~~~

* [ADD] Multimodal file support for images, PDFs, and text files
* [IMP] Refactored to use base module's _prepare_multimodal_attachments() method
* [IMP] Removed duplicate attachment handling code

18.0.1.3.0 (2026-01-07)
~~~~~~~~~~~~~~~~~~~~~~~

* [REM] Removed provider and model data files - users now create providers manually
* [IMP] Provider/model data is now user-owned and survives module uninstall

18.0.1.2.0 (2025-11-28)
~~~~~~~~~~~~~~~~~~~~~~~

* [ADD] Added openai_normalize_prepend_messages() for dispatch pattern compliance
* [IMP] Changed openai_chat to use generic format_messages() and format_tools() dispatch methods
* [IMP] Improved consistency with base provider dispatch pattern

18.0.1.1.4 (2025-11-17)
~~~~~~~~~~~~~~~~~~~~~~~

* [FIX] Updated batch job processing to use provider's _determine_model_use() method instead of wizard

18.0.1.1.3 (2025-10-23)
~~~~~~~~~~~~~~~~~~~~~~~

* [MIGRATION] Migrated to Odoo 18.0

16.0.1.1.3 (2025-05-13)
~~~~~~~~~~~~~~~~~~~~~~~

* [FIX] Fine tuning support

16.0.1.1.2 (2025-04-08)
~~~~~~~~~~~~~~~~~~~~~~~

* [IMP] Added workaround for Gemini API compatibility (generates placeholder `tool_call_id` if missing)
* [IMP] Modified message formatting to conditionally include `content` key for Gemini compatibility
* [FIX] Fixed errors when using Gemini API due to missing `tool_call_id`

16.0.1.1.1 (2025-04-03)
~~~~~~~~~~~~~~~~~~~~~~~

* [FIX] Added default model for OpenAI, will work when user adds API key

16.0.1.1.0 (2025-03-06)
~~~~~~~~~~~~~~~~~~~~~~~

* [ADD] Tool support for OpenAI models - Implemented function calling capabilities
* [IMP] Enhanced message handling for tool execution
* [IMP] Added support for processing tool results in chat context

16.0.1.0.0 (2025-01-02)
~~~~~~~~~~~~~~~~~~~~~~~

* [INIT] Initial release of the module
