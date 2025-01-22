import logging
from odoo import fields, models
import markdown2
import re

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
        """Handle message posting and trigger AI response if needed."""
        res = super()._message_post_after_hook(message, msg_vals)

        # Only generate response for user messages
        if (msg_vals.get('subtype_id') == self.env.ref('llm_thread.mt_llm_question').id and
            not self.env.context.get('skip_ai_response')):  # Not already an AI response
            
            llm_thread = self.env['llm.thread'].get_user_thread(
                self._name, self.id
            )
            
            if llm_thread:
                try:
                    # Get AI response (non-streaming for hook)
                    accumulated_content = ""
                    for response in llm_thread.generate_response(message):
                        if response.get('error'):
                            _logger.error("Error getting AI response: %s", response['error'])
                            break
                        
                        content = response.get('content', '')
                        if content:
                            accumulated_content += content
                    
                    # Post accumulated response
                    if accumulated_content:
                        self.with_context(
                            skip_ai_response=True,
                            mail_create_nosubscribe=True
                        )._post_ai_response(llm_thread, accumulated_content)
                            
                except Exception as e:
                    _logger.exception("Failed to generate AI response")
        else:
            _logger.debug("Skipping AI Response: %s", {
                'is_comment': msg_vals.get('message_type') == 'comment',
                'has_author': bool(msg_vals.get('author_id')),
                'skip_response': bool(self.env.context.get('skip_ai_response'))
            })
                
        return res
    
    def _markdown_to_html(self, content):
        """Convert markdown content to HTML suitable for Odoo messages.
        
        Args:
            content (str): Markdown formatted content
            
        Returns:
            str: HTML content wrapped in appropriate Odoo classes
        """
        # Convert markdown to HTML with extras for better formatting
        html_content = markdown2.markdown(content, extras=[
            'fenced-code-blocks',  # Support ```code blocks```
            'tables',              # Support markdown tables
            'break-on-newline',    # Convert newlines to <br>
            'header-ids',          # Add ids to headers
            'code-friendly',       # Better code block handling
            'smarty-pants',        # Smart quotes, dashes, etc.
        ])
        
        # Clean up any existing div wrappers
        html_content = re.sub(r'<div[^>]*>', '', html_content)
        html_content = html_content.replace('</div>', '')
        
        # Wrap code blocks with pre tags and add syntax highlighting class
        html_content = html_content.replace(
            '<code>', 
            '<pre class="o_codeblock"><code>'
        ).replace('</code>', '</code></pre>')
        
        # Ensure proper wrapping without double-escaping
        return f'<div class="o_mail_note_content">{html_content}</div>'
        
    def _post_ai_response(self, llm_thread, content):
        """Post AI response message with proper settings"""
        safe_content = self._markdown_to_html(content)
        
        return self.message_post(
            body=safe_content,
            message_type='comment',
            subtype_xmlid='llm_thread.mt_llm_answer',
            author_id=False,  # No author for AI messages
            email_from=f"{llm_thread.model_id.name} <ai@{llm_thread.provider_id.name.lower()}.ai>",
            partner_ids=[],  # No partner notifications
        )