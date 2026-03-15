18.0.1.5.4 (2025-12-02)
~~~~~~~~~~~~~~~~~~~~~~~

* [FIX] Removed invalid `unaccent` parameter from parent_path field (Odoo 18 compatibility)
* [FIX] Added missing access rules for llm.thread.mock transient model

18.0.1.5.3 (2025-12-02)
~~~~~~~~~~~~~~~~~~~~~~~

* [FIX] Replaced bus notification with client action for "Process with AI" button reliability
* [ADD] New client action llm_open_ai_chat_in_chatter for reliable AI chat opening
* [IMP] action_open_llm_assistant() now returns ir.actions.client instead of bus notification
* [IMP] Works reliably on cloud deployments with WebSocket/bus issues

18.0.1.5.2 (2025-11-26)
~~~~~~~~~~~~~~~~~~~~~~~

* [FIX] Moved prompt_id serialization to _thread_to_store() from llm_thread module
* [IMP] prompt_id handling now properly resides in the module that defines the field

18.0.1.5.1 (2025-11-21)
~~~~~~~~~~~~~~~~~~~~~~~

* [IMP] Simplified action_open_llm_assistant by removing unused pre/post action hooks
* [IMP] Enhanced thread naming in mixin - backend now generates names from record display_name
* [FIX] Cleaned up unnecessary kwargs handling for better maintainability

18.0.1.5.0 (2025-10-23)
~~~~~~~~~~~~~~~~~~~~~~~

* [MIGRATION] Migrated to Odoo 18.0
* [IMP] Updated views and OWL components for compatibility

16.0.1.5.0 (2025-07-13)
~~~~~~~~~~~~~~~~~~~~~~~

* [ADD] Assistant code system with unique constraint
* [ADD] Model association via res_model field
* [ADD] Default assistant system with is_default flag
* [ADD] get_assistant_by_code() discovery method
* [MIGRATION] Auto-generate codes from category hierarchy

16.0.1.0.1 (2025-04-04)
~~~~~~~~~~~~~~~~~~~~~~~

* [ADD] Assistant Creator assistant data record
* [ADD] Data directory structure

16.0.1.0.0 (2025-03-01)
~~~~~~~~~~~~~~~~~~~~~~~

* [INIT] Initial release
