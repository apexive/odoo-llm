import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Post-migration script to clean up old template tables after successful migration
    """
    _logger.info("Starting post-migration cleanup for LLM prompt refactor")

    try:
        # Check if all prompts have been migrated (have template field populated)
        cr.execute("""
            SELECT COUNT(*) FROM llm_prompt 
            WHERE template IS NULL OR template = ''
        """)
        unmigrated_count = cr.fetchone()[0]

        if unmigrated_count > 0:
            _logger.warning(f"Found {unmigrated_count} prompts without templates. Skipping cleanup.")
            return

        # Drop the old template table
        _logger.info("Dropping llm_prompt_template table")
        cr.execute("DROP TABLE IF EXISTS llm_prompt_template CASCADE")

        # Remove template_count computed field references if they exist in other tables
        # This might need to be adjusted based on your specific schema

        _logger.info("Post-migration cleanup completed successfully")

    except Exception as e:
        _logger.error(f"Error during post-migration cleanup: {str(e)}")
        # Don't raise the exception as migration should continue even if cleanup fails
