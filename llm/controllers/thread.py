from odoo import http
from odoo.http import request
from werkzeug.wrappers import Response


class LLMThreadController(http.Controller):
    @http.route("/llm/thread/data", type="json", auth="user")
    def get_thread_data(self, thread_id):
        thread = request.env["llm.thread"].browse(int(thread_id))
        return thread.get_thread_data()

    @http.route("/llm/thread/post_message", type="json", auth="user")
    def post_message(self, thread_id, content, role="user", stream=False):
        thread = request.env["llm.thread"].browse(int(thread_id))

        if stream:
            response = Response(thread.post_message(content, role=role, stream=stream))
            response.direct_passthrough = True
            return response
        else:
            for m in thread.post_message(content, role=role, stream=stream):
                pass
        return []
