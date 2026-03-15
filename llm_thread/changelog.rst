18.0.1.4.5 (2026-01-17)
~~~~~~~~~~~~~~~~~~~~~~~

* [ADD] Unsupported file detection with is_error message exclusion
* [ADD] New _post_error_message() for displaying API errors in thread
* [ADD] New _check_unsupported_attachments() for file compatibility validation
* [ADD] is_error parameter to message_post() for error message tracking
* [IMP] Error messages excluded from LLM context via is_error=False filter
* [IMP] Skip markdown processing for pre-formatted Markup content

18.0.1.4.4 (2026-01-16)
~~~~~~~~~~~~~~~~~~~~~~~

* [ADD] Multimodal file attachment support in chat interface
* [FIX] Restored nginx buffering comment for SSE streaming documentation

18.0.1.4.3 (2025-12-02)
~~~~~~~~~~~~~~~~~~~~~~~

* [FIX] Replaced unreliable bus notification with client action pattern for AI chat opening
* [IMP] Added pendingOpenInChatter state to llm.store service for cross-navigation state
* [IMP] Added checkPendingAIChatOpen() method to chatter patch
* [REMOVE] Removed redundant bus subscription code from chatter patch

18.0.1.4.2 (2025-11-26)
~~~~~~~~~~~~~~~~~~~~~~~

* [FIX] Removed prompt_id reference from _thread_to_store() - field is defined in llm_assistant
* [IMP] Module can now be installed standalone without llm_assistant dependency

18.0.1.4.1 (2025-11-21)
~~~~~~~~~~~~~~~~~~~~~~~

* [FIX] Fixed broken create() method using self.model_id in @api.model context
* [IMP] Unified thread naming with backend-generated names using record display_name
* [IMP] Added unique ID suffix to standalone thread names (e.g., "New Chat #123")
* [IMP] Proper @api.model_create_multi decorator for batch creation support
* [REMOVE] Removed hardcoded name generation from chatter patch and client action

18.0.1.4.0 (2025-10-23)
~~~~~~~~~~~~~~~~~~~~~~~

* [ADD] Related Record component - Link chat threads to any Odoo record
* [IMP] Service layer architecture for record linking/unlinking
* [FIX] Field naming collision in store serialization (model vs res_model)
* [MIGRATION] Replace name_get() with searchRead() for Odoo 18.0 compatibility

18.0.1.3.0 (2025-01-04)
~~~~~~~~~~~~~~~~~~~~~~~

* [BREAKING] Refactored to use stored llm_role field for maximum efficiency
* [PERF] Added computed stored llm_role field for instant role lookups
* [PERF] Optimized message queries using direct field filtering instead of batch methods
* [PERF] Improved frontend performance with direct field comparison instead of computed properties
* [PERF] Enhanced database performance with proper indexing on llm_role field
* [IMP] Simplified message_post API with llm_role parameter instead of subtype_xmlid
* [IMP] Updated JavaScript models to use direct field access for role checking
* [IMP] Streamlined message template rendering with direct field conditionals
* [IMP] Simplified message action visibility logic with direct role comparison
* [MIGRATION] Added migration script to compute llm_role for existing messages
* [REMOVE] Removed complex role checking computed properties (replaced with direct field access)
* [OPT] Leveraged database indexing for improved query performance on llm_role field

16.0.1.2.0 (2025-01-04)
~~~~~~~~~~~~~~~~~~~~~~~

* [BREAKING] Refactored to use LLM base module message subtypes instead of separate llm_mail_message_subtypes module
* [MIGRATION] Added migration script to convert existing message subtypes to new format
* [REMOVE] Removed dependency on llm_mail_message_subtypes module
* [IMP] Simplified subtype handling by using direct XML IDs from llm base module
* [OPT] Optimized XML ID resolution using _xmlid_to_res_id instead of env.ref

16.0.1.1.1 (2025-04-09)
~~~~~~~~~~~~~~~~~~~~~~~

* [FIX] Update method names to be consistent

16.0.1.1.0 (2025-03-06)
~~~~~~~~~~~~~~~~~~~~~~~

* [ADD] Tool integration in chat interface - Support for displaying tool executions and results
* [IMP] Enhanced UI for tool messages with cog icon and argument display
* [IMP] Updated chat components to handle tool-related message types

16.0.1.0.0 (2025-01-02)
~~~~~~~~~~~~~~~~~~~~~~~

* [INIT] Initial release of the module
