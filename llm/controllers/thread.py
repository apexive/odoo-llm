from odoo import http
from odoo.http import request, Response
import werkzeug
import json

class LLMThreadController(http.Controller):
    @http.route("/llm/thread/data", type="json", auth="user")
    def get_thread_data(self, thread_id):
        thread = request.env["llm.thread"].browse(int(thread_id))
        return thread.get_thread_data()

    @http.route("/llm/thread/post_message", type="json", auth="user")
    def post_message(self, thread_id, content, role="user"):
        """Simply post a message to the thread"""
        thread = request.env["llm.thread"].browse(int(thread_id))
        message = thread.post_message(content=content, role=role)
        return message.to_frontend_data()

    @http.route("/llm/thread/get_assistant_response", type="json", auth="user", csrf=True)
    def get_assistant_response(self, thread_id):
        """Get assistant response with proper CSRF protection"""
        try:
            thread = request.env["llm.thread"].browse(int(thread_id))
            responses = []

            # Collect all responses from the generator
            for response in thread.get_assistant_response(stream=True):
                if response.get("error"):
                    return {"error": response["error"]}
                responses.append(response)

            return responses

        except Exception as e:
            return {"error": str(e)}
