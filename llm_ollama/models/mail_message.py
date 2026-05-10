import json
import logging

from odoo import models, tools

from ..utils.ollama_tool_call_id_utils import OllamaToolCallIdUtils

_logger = logging.getLogger(__name__)


class MailMessage(models.Model):
    _inherit = "mail.message"

    def ollama_format_message(self):
        """Provider-specific formatting for Ollama."""
        self.ensure_one()
        body = self.body
        if body:
            body = tools.html2plaintext(body)

        if self.is_llm_user_message()[self]:
            formatted_message = {"role": "user"}
            if body:
                formatted_message["content"] = body
            return formatted_message

        elif self.is_llm_assistant_message()[self]:
            formatted_message = {"role": "assistant"}
            content = tools.html2plaintext(self.body) if self.body else ""
            if content:
                formatted_message["content"] = content

            # Add tool calls if present in body_json
            tool_calls = self.get_tool_calls()
            if tool_calls:
                formatted_message["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": tc.get("type", "function"),
                        "function": {
                            "name": tc["function"]["name"],
                            "arguments": tc["function"]["arguments"],
                        },
                    }
                    for tc in tool_calls
                ]

            return formatted_message

        elif self.llm_role == "tool":
            tool_data = self.body_json
            if not tool_data:
                _logger.warning(
                    f"Ollama Format: Skipping tool message {self.id}: no tool data found."
                )
                return None

            tool_name = tool_data.get("tool_name")
            if not tool_name:
                # Fallback to extracting from tool_call_id
                tool_call_id = tool_data.get("tool_call_id")
                if tool_call_id:
                    tool_name = OllamaToolCallIdUtils.extract_tool_name_from_id(
                        tool_call_id
                    )

            if not tool_name:
                _logger.warning(
                    f"Ollama Format: Skipping tool message {self.id}: missing tool_name."
                )
                return None

            # Get result content
            if "result" in tool_data:
                content = json.dumps(tool_data["result"])
            elif "error" in tool_data:
                content = json.dumps({"error": tool_data["error"]})
            else:
                content = ""

            formatted_message = {
                "role": "tool",
                "name": tool_name,
                "content": content,
            }
            return formatted_message
        else:
            return None
