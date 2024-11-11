import json
import logging

from odoo import api, http, registry
from odoo.http import Response, request

_logger = logging.getLogger(__name__)


class LLMThreadController(http.Controller):
    @http.route("/llm/thread/data", type="json", auth="user")
    def get_thread_data(self, thread_id):
        thread = request.env["llm.thread"].browse(int(thread_id))
        return thread.get_thread_data()

    @http.route("/llm/thread/post_message", type="json", auth="user")
    def post_message(self, thread_id, content, role="user"):
        thread = request.env["llm.thread"].browse(int(thread_id))
        message = thread.post_message(content=content, role=role)
        return message.to_frontend_data()

    def generate(self, dbname, env, thread_id):
        with registry(dbname).cursor() as cr:
            env = api.Environment(cr, env.uid, env.context)
            thread = env["llm.thread"].browse(int(thread_id))

            # Convert string data to bytes for all yields
            yield f"data: {json.dumps({'type': 'start'})}\n\n".encode()

            # Stream responses
            for response in thread.get_assistant_response(stream=True):
                if response.get("error"):
                    error_data = f"data: {json.dumps({'type': 'error', 'error': response['error']})}\n\n"
                    yield error_data.encode("utf-8")
                    break

                if response.get("content"):
                    content_data = f"data: {json.dumps({'type': 'content', 'content': response['content']})}\n\n"
                    yield content_data.encode("utf-8")

            # Send end event
            yield f"data: {json.dumps({'type': 'end'})}\n\n".encode()

    @http.route("/llm/thread/stream_response", type="http", auth="user", csrf=True)
    def stream_response(self, thread_id):
        """Stream assistant responses using server-sent events"""
        headers = {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }

        return Response(
            self.generate(request.cr.dbname, request.env, thread_id),
            direct_passthrough=True,
            headers=headers,
        )

    @http.route("/llm/thread/<int:thread_id>/export", type="http", auth="user")
    def export_thread(self, thread_id):
        """Export thread messages as text file"""
        try:
            thread = request.env["llm.thread"].browse(int(thread_id))

            # Generate export content
            content = []
            for message in thread.message_ids:
                author = message.get_author_name()
                content.append(f"{author} ({message.role}):")
                content.append(message.content)
                content.append("")  # Empty line between messages

            export_text = "\n".join(content)

            # Generate filename
            filename = f"chat_export_{thread.id}.txt"

            # Return file response with proper encoding
            return request.make_response(
                export_text.encode("utf-8"),
                headers=[
                    ("Content-Type", "text/plain; charset=utf-8"),
                    ("Content-Disposition", f'attachment; filename="{filename}"'),
                ],
            )

        except Exception:
            _logger.exception("Error exporting thread")
            return request.not_found()
