18.0.1.0.0 (2025-10-23)
~~~~~~~~~~~~~~~~~~~~~~~

* [MIGRATION] Migrated to Odoo 18.0
* [FIX] Removed deprecated numbercall field from cron jobs
* [IMP] Updated views (tree→list, attrs→direct attributes)

16.0.1.0.0 (2025-01-07)
~~~~~~~~~~~~~~~~~~~~~~~

* [INIT] Initial release of LLM Generate Job module (renamed from LLM Generation Job)
* [ADD] Generation job lifecycle management (Draft → Queued → Running → Completed/Failed/Cancelled)
* [ADD] Provider-specific queue management with concurrency control
* [ADD] Flexible generation options (direct vs queued)
* [ADD] Comprehensive job monitoring and statistics
* [ADD] Auto-retry mechanism for failed jobs
* [ADD] Performance metrics and queue health monitoring
* [ADD] Cron jobs for queue processing and status checking
* [ADD] Management views for jobs and queues
* [ADD] Provider integration interface with fallback to direct generation
* [ADD] PostgreSQL advisory locking integration
* [ADD] Security access rights for users and managers
* [FEAT] Backward compatibility with existing generation system
* [FEAT] Input/output message tracking with renamed fields (input_message_id, output_message_id)
* [FEAT] Real-time job status updates and progress monitoring
* [REFACTOR] Thread extension now only overrides generate_response() method instead of generate()
