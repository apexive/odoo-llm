from odoo import http
from odoo.http import request

class LLMThreadController(http.Controller):
    @http.route("/llm/thread/user", type="json", auth="user")
    def get_user_thread(self, record_model_name, record_id):
        """Get user's LLM thread for a record"""
        thread = request.env['llm.thread'].get_user_thread(record_model_name, int(record_id))
        if not thread:
            return {'error': 'No LLM thread found'}
        
        return {
            'thread_id': thread.id,
            'provider_id': thread.provider_id.id,
            'provider_name': thread.provider_id.name,
            'model_id': thread.model_id.id,
            'model_name': thread.model_id.name,
        }
    
    @http.route("/llm/thread/update", type="json", auth="user")
    def update_config(self, thread_id, provider_id=None, model_id=None):
        """Update user's LLM thread"""
        thread = request.env['llm.thread'].browse(int(thread_id))
        if not thread.exists() or thread.user_id != request.env.user:
            return {'error': 'Invalid thread'}
            
        vals = {}
        if provider_id:
            vals['provider_id'] = int(provider_id)
        if model_id:
            vals['model_id'] = int(model_id)
            
        if vals:
            thread.write(vals)
            
        return self.get_user_thread(thread.res_model, thread.res_id)
        
    @http.route("/llm/thread/create", type="json", auth="user")
    def create_thread(self, model, record_id, provider_id, model_id):
        """Create new LLM thread"""
        vals = {
            'user_id': request.env.user.id,
            'res_model': model,
            'res_id': int(record_id),
            'provider_id': int(provider_id),
            'model_id': int(model_id),
        }
        
        request.env['llm.thread'].create(vals)
        return self.get_user_thread(model, record_id)