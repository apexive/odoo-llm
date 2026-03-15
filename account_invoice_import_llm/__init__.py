import logging

from . import models
from . import wizard

_logger = logging.getLogger(__name__)


def pre_init_hook(env):
    """Adopt orphaned records from old module (llm_assistant_account_invoice)."""
    cr = env.cr
    _logger.info("Adopting orphaned records from llm_assistant_account_invoice")

    # Update ir_model_data records from old module name
    cr.execute("""
        UPDATE ir_model_data
        SET module = 'account_invoice_import_llm'
        WHERE module = 'llm_assistant_account_invoice'
    """)
    if cr.rowcount:
        _logger.info("Updated %d ir_model_data records", cr.rowcount)

    # Adopt orphaned prompt
    cr.execute("""
        INSERT INTO ir_model_data (name, module, model, res_id, noupdate)
        SELECT 'llm_prompt_invoice_extraction', 'account_invoice_import_llm', 'llm.prompt', id, false
        FROM llm_prompt
        WHERE name = 'Invoice Data Extraction (One-Shot)'
        AND id NOT IN (SELECT res_id FROM ir_model_data WHERE model = 'llm.prompt')
        ON CONFLICT DO NOTHING
    """)
    if cr.rowcount:
        _logger.info("Adopted orphaned llm_prompt")

    # Adopt orphaned assistant
    cr.execute("""
        INSERT INTO ir_model_data (name, module, model, res_id, noupdate)
        SELECT 'llm_assistant_invoice_extraction', 'account_invoice_import_llm', 'llm.assistant', id, false
        FROM llm_assistant
        WHERE code = 'invoice_extraction'
        AND id NOT IN (SELECT res_id FROM ir_model_data WHERE model = 'llm.assistant')
        ON CONFLICT DO NOTHING
    """)
    if cr.rowcount:
        _logger.info("Adopted orphaned llm_assistant")
