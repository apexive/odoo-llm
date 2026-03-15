18.0.1.7.0 (2026-01-17)
~~~~~~~~~~~~~~~~~~~~~~~

* [ADD] Multimodal file support for images, PDFs, and text files
* [ADD] New is_error field for excluding error messages from LLM context
* [ADD] New _get_attachments_by_mimetype() base method for DRY attachment handling
* [ADD] New _get_unsupported_attachments() for file compatibility validation
* [ADD] AUDIO/VIDEO/OFFICE_MIMETYPES constants for file type detection
* [IMP] Refactored _get_image/pdf/text/audio_attachments() to use base method

18.0.1.6.0 (2026-01-07)
~~~~~~~~~~~~~~~~~~~~~~~

* [IMP] LLM Manager role now auto-implied for admin users (base.group_system)
* [IMP] Removed manual user assignment in favor of group implication

18.0.1.5.0 (2025-11-28)
~~~~~~~~~~~~~~~~~~~~~~~

* [ADD] Added _extract_content_text() helper for extracting text from message content (handles both string and OpenAI list formats)
* [ADD] Added _dispatch("normalize_prepend_messages") call in chat() for provider-specific message normalization
* [IMP] Improved dispatch pattern consistency for prepend_messages handling

18.0.1.4.1 (2025-11-17)
~~~~~~~~~~~~~~~~~~~~~~~

* [FIX] Fixed wizard_id not being set on llm.fetch.models.line records
* [IMP] Refactored model fetching: moved logic from wizard default_get() to provider action_fetch_models()
* [IMP] Moved _determine_model_use() from wizard to provider for better extensibility
* [REM] Removed wizard write() override workaround
* [ADD] Comprehensive docstrings with extension pattern examples
* [ADD] Documented standard capability names and priority order

18.0.1.4.0 (2025-10-23)
~~~~~~~~~~~~~~~~~~~~~~~

* [MIGRATION] Migrated to Odoo 18.0
* [IMP] Updated views and manifest for compatibility

16.0.1.3.0
~~~~~~~~~~

* [BREAKING] Moved message subtypes to base module
* [ADD] Added required `llm_role` field computation with automatic migration
* [IMP] Enhanced provider dispatch mechanism
* [MIGRATION] Automatic computation of `llm_role` for existing messages
* [MIGRATION] Database migration creates indexes for performance

16.0.1.1.0 (2025-03-06)
~~~~~~~~~~~~~~~~~~~~~~~

* [ADD] Tool support framework in base LLM models
* [IMP] Enhanced provider interface to support tool execution
* [IMP] Updated model handling for function calling capabilities

16.0.1.0.0 (2025-01-02)
~~~~~~~~~~~~~~~~~~~~~~~

* [INIT] Initial release
