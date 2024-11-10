from odoo import http
from odoo.http import request

class LLMThreadController(http.Controller):
    @http.route('/llm/thread/data', type='json', auth='user')
    def get_thread_data(self, thread_id):
        thread = request.env['llm.thread'].browse(int(thread_id))
        return thread.get_thread_data()

    @http.route('/llm/thread/post_message', type='json', auth='user')
    def post_message(self, thread_id, content, role):
        thread = request.env['llm.thread'].browse(int(thread_id))
        return thread.send_message(content, role)
