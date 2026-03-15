"""Migration script for consolidating llm_resource into llm_knowledge

This migration handles the consolidation of the llm_resource module
into the llm_knowledge module.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Migration script to handle llm_resource consolidation"""

    # Check if llm_resource module exists and mark it as uninstalled
    cr.execute("""
        SELECT id FROM ir_module_module
        WHERE name = 'llm_resource' AND state = 'installed'
    """)

    llm_resource_module = cr.fetchone()
    if llm_resource_module:
        _logger.info("Found installed llm_resource module, marking as uninstalled")

        # Mark llm_resource as uninstalled
        cr.execute("""
            UPDATE ir_module_module
            SET state = 'uninstalled'
            WHERE name = 'llm_resource'
        """)

        # Remove any ir_model_data entries that reference llm_resource
        cr.execute("""
            DELETE FROM ir_model_data
            WHERE module = 'llm_resource'
        """)

        _logger.info("Successfully marked llm_resource as uninstalled")
    else:
        _logger.info("llm_resource module not found or already uninstalled")

    # Update any external references in ir_model_data to point to llm_knowledge
    cr.execute("""
        UPDATE ir_model_data
        SET module = 'llm_knowledge'
        WHERE name LIKE '%llm_resource%' AND module != 'llm_knowledge'
    """)

    _logger.info("Migration completed successfully")
