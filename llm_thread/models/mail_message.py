import logging
from odoo import fields, models

_logger = logging.getLogger(__name__)

class MailMessage(models.Model):
    _inherit = 'mail.message'
    
    llm_thread_id = fields.Many2one('llm.thread', 
        help="The LLM thread that generated this message (for AI responses)")
    
    def _to_llm_format(self):
        """Convert message to LLM format"""
        return {
            'role': 'assistant' if self.subtype_id == self.env.ref('llm_thread.mt_llm_answer') else 'user',
            'content': self.body
        }