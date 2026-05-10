import json
import logging

from odoo import models, tools

_logger = logging.getLogger(__name__)


class MailMessage(models.Model):
    _inherit = "mail.message"

    def anthropic_format_message(self, is_multimodal=False):
        """Provider-specific formatting for Anthropic Claude.

        Key differences from OpenAI:
        - Tool results use role="user" with content type "tool_result"
        - Assistant messages with tool calls use content as array of blocks
        - Content can be string or list of content blocks
        """
        self.ensure_one()
        body = self.body
        if body:
            body = tools.html2plaintext(body)

        if self.is_llm_user_message()[self]:
            texts = self._get_text_attachments()

            # Only include images/PDFs if model supports multimodal
            if is_multimodal:
                images = self._get_image_attachments()
                pdfs = self._get_pdf_attachments()
            else:
                images = []
                pdfs = []

            has_attachments = images or pdfs or texts

            if has_attachments:
                content = []

                for img in images:
                    content.append(
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": img["mimetype"],
                                "data": img["data"],
                            },
                        },
                    )

                for pdf in pdfs:
                    content.append(
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": pdf["mimetype"],
                                "data": pdf["data"],
                            },
                        },
                    )

                text_parts = []
                if body and body.strip():
                    text_parts.append(body.strip())

                for txt in texts:
                    text_parts.append(f"--- {txt['name']} ---\n{txt['content']}")

                if text_parts:
                    content.append({"type": "text", "text": "\n\n".join(text_parts)})
                elif images or pdfs:
                    content.append(
                        {"type": "text", "text": "Please analyze these files."},
                    )

                return {"role": "user", "content": content}

            if not body or not body.strip():
                return None
            return {"role": "user", "content": body}

        if self.is_llm_assistant_message()[self]:
            content_blocks = []

            if body:
                content_blocks.append({"type": "text", "text": body})

            tool_calls = self.get_tool_calls()
            if tool_calls:
                for tc in tool_calls:
                    try:
                        tool_input = json.loads(tc["function"]["arguments"])
                    except (json.JSONDecodeError, KeyError, TypeError):
                        tool_input = {}

                    content_blocks.append(
                        {
                            "type": "tool_use",
                            "id": tc["id"],
                            "name": tc["function"]["name"],
                            "input": tool_input,
                        },
                    )

            if content_blocks:
                return {"role": "assistant", "content": content_blocks}
            return None

        if self.is_llm_tool_message()[self]:
            tool_data = self.body_json
            if not tool_data:
                _logger.warning(
                    f"Anthropic Format: Skipping tool message {self.id}: no tool data found.",
                )
                return None

            tool_call_id = tool_data.get("tool_call_id")
            if not tool_call_id:
                _logger.warning(
                    f"Anthropic Format: Skipping tool message {self.id}: missing tool_call_id.",
                )
                return None

            if "result" in tool_data:
                content = json.dumps(tool_data["result"])
            elif "error" in tool_data:
                content = json.dumps({"error": tool_data["error"]})
            else:
                content = ""

            return {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_call_id,
                        "content": content,
                    },
                ],
            }

        return None
