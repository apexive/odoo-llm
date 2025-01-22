import logging
from odoo import fields, models

_logger = logging.getLogger(__name__)

class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'
    
    llm_thread_ids = fields.One2many(
        'llm.thread', 
        compute='_compute_llm_thread_ids'
    )
    
    def _compute_llm_thread_ids(self):
        """Compute all LLM threads for this record"""
        for record in self:
            record.llm_thread_ids = self.env['llm.thread'].search(
                self.env['llm.thread']._get_thread_domain(
                    False,  # Get all users' threads
                    record._name, 
                    record.id
                )
            )
    
    def _message_post_after_hook(self, message, msg_vals):
        """Handle AI response generation after message post"""
        res = super()._message_post_after_hook(message, msg_vals)
        
        if (msg_vals.get('subtype_id') == self.env.ref('llm_thread.mt_llm_question').id and
            not self.env.context.get('skip_ai_response')):
            
            llm_thread = self.env['llm.thread'].get_user_thread(
                self._name, self.id
            )
            
            if llm_thread:
                response = llm_thread.generate_response(message)
                if not response.get('error'):
                    self._post_ai_response(llm_thread, response['content'])
        
        return res
        
    def _post_ai_response(self, llm_thread, content):
        """Post AI response message"""
        return self.with_context(
            skip_ai_response=True,
            mail_create_nosubscribe=True,
            llm_thread_id=llm_thread.id
        ).message_post(
            body=content,
            message_type='comment',
            subtype_xmlid='llm_thread.mt_llm_answer',
            author_id=False,
            email_from=f"{llm_thread.model_id.name} <ai@{llm_thread.provider_id.name.lower()}.ai>"
        )
