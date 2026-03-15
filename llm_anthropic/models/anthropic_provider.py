import json
import logging

from anthropic import Anthropic

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class LLMProvider(models.Model):
    _inherit = "llm.provider"

    @api.model
    def _get_available_services(self):
        """Register Anthropic as an available service."""
        services = super()._get_available_services()
        return services + [("anthropic", "Anthropic")]

    def anthropic_get_client(self):
        """Get Anthropic client instance."""
        self.ensure_one()
        if not self.api_key:
            raise UserError(_("API key is required for Anthropic provider"))
        return Anthropic(api_key=self.api_key)

    def anthropic_normalize_prepend_messages(self, prepend_messages):
        """Normalize prepend messages for Anthropic format.

        System messages are kept in the list and extracted later in chat().
        This ensures proper handling of all message types.
        """
        if not prepend_messages:
            return []

        normalized = []
        for msg in prepend_messages:
            content = msg.get("content", "")
            if isinstance(content, str) or isinstance(content, list):
                normalized.append({"role": msg["role"], "content": content})
            else:
                normalized.append(msg)

        return normalized

    def anthropic_chat(
        self,
        messages,
        model=None,
        stream=False,
        tools=None,
        prepend_messages=None,
        **kwargs,
    ):
        """Send chat messages using Anthropic Claude.

        Key differences from OpenAI:
        - System message is a separate parameter, not in messages array
        - Tool format: {"name", "description", "input_schema"}
        - Response: content blocks array, not single content string
        - Tool use: content block with type="tool_use"

        Args:
            messages: mail.message recordset to send
            model: Optional specific model to use
            stream: Whether to stream the response
            tools: llm.tool recordset of available tools
            prepend_messages: List of pre-formatted message dicts
            **kwargs: Additional parameters (max_tokens, extended_thinking, etc.)

        Returns:
            Generator if streaming, else dict with 'content' and/or 'tool_calls'
        """
        model = self.get_model(model, "chat")
        formatted_messages = self.format_messages(messages, model=model)

        system_content = None
        if prepend_messages:
            for msg in prepend_messages:
                if msg.get("role") == "system":
                    system_content = self._extract_content_text(msg.get("content", ""))
                    break

            non_system_prepend = [
                m for m in prepend_messages if m.get("role") != "system"
            ]
            formatted_messages = non_system_prepend + formatted_messages

        params = {
            "model": model.name,
            "messages": formatted_messages,
            "max_tokens": kwargs.get("max_tokens", 4096),
        }

        if system_content:
            params["system"] = system_content

        if tools:
            formatted_tools = self.format_tools(tools)
            if formatted_tools:
                params["tools"] = formatted_tools

        if kwargs.get("extended_thinking"):
            params["thinking"] = {
                "type": "enabled",
                "budget_tokens": kwargs.get("thinking_budget", 10000),
            }

        if stream:
            return self._anthropic_stream_response(params)
        return self._anthropic_process_response(params)

    def _anthropic_process_response(self, params):
        """Process non-streaming response from Anthropic.

        Returns:
            dict: {"content": str} and/or {"tool_calls": list} and/or {"thinking": str}
        """
        response = self.client.messages.create(**params)
        result = {}
        thinking_content = []

        for block in response.content:
            if block.type == "thinking":
                thinking_content.append(block.thinking)
            elif block.type == "text":
                result["content"] = result.get("content", "") + block.text
            elif block.type == "tool_use":
                if "tool_calls" not in result:
                    result["tool_calls"] = []
                result["tool_calls"].append(
                    {
                        "id": block.id,
                        "type": "function",
                        "function": {
                            "name": block.name,
                            "arguments": json.dumps(block.input),
                        },
                    },
                )

        if thinking_content:
            result["thinking"] = "\n".join(thinking_content)

        return result

    def _anthropic_stream_response(self, params):
        """Process streaming response from Anthropic.

        Yields:
            dict: {"content": str} or {"tool_calls": list} or {"thinking": str}
        """
        with self.client.messages.stream(**params) as stream:
            tool_calls = {}
            current_thinking = ""

            for event in stream:
                if event.type == "content_block_start":
                    if event.content_block.type == "tool_use":
                        tool_calls[event.index] = {
                            "id": event.content_block.id,
                            "name": event.content_block.name,
                            "input": "",
                        }
                    elif event.content_block.type == "thinking":
                        current_thinking = ""

                elif event.type == "content_block_delta":
                    if hasattr(event.delta, "text"):
                        yield {"content": event.delta.text}
                    elif hasattr(event.delta, "thinking"):
                        current_thinking += event.delta.thinking
                        yield {"thinking": event.delta.thinking}
                    elif hasattr(event.delta, "partial_json"):
                        if event.index in tool_calls:
                            tool_calls[event.index]["input"] += event.delta.partial_json

                elif event.type == "content_block_stop":
                    if event.index in tool_calls:
                        tc = tool_calls[event.index]
                        try:
                            parsed_input = (
                                json.loads(tc["input"]) if tc["input"] else {}
                            )
                        except json.JSONDecodeError:
                            parsed_input = {}

                        yield {
                            "tool_calls": [
                                {
                                    "id": tc["id"],
                                    "type": "function",
                                    "function": {
                                        "name": tc["name"],
                                        "arguments": json.dumps(parsed_input),
                                    },
                                },
                            ],
                        }
                        del tool_calls[event.index]

    def anthropic_format_tools(self, tools):
        """Format tools for Anthropic API.

        Anthropic tool format:
        {
            "name": "tool_name",
            "description": "Tool description",
            "input_schema": {
                "type": "object",
                "properties": {...},
                "required": [...]
            }
        }
        """
        formatted = []
        for tool in tools:
            try:
                if tool.input_schema:
                    schema = json.loads(tool.input_schema)
                else:
                    schema = (
                        tool.get_input_schema()
                        if hasattr(tool, "get_input_schema")
                        else {}
                    )
            except (json.JSONDecodeError, TypeError):
                schema = {}

            formatted.append(
                {
                    "name": tool.name,
                    "description": tool.description or "",
                    "input_schema": {
                        "type": "object",
                        "properties": schema.get("properties", {}),
                        "required": schema.get("required", []),
                    },
                },
            )

        return formatted

    def anthropic_format_messages(self, messages, system_prompt=None, model=None):
        """Format mail.message records for Anthropic API.

        Note: System prompts are handled separately in anthropic_chat(),
        not included in the messages array.

        Args:
            messages: mail.message recordset
            system_prompt: Optional system prompt (handled separately)
            model: llm.model record (to determine if multimodal)

        Returns:
            List of formatted messages for Anthropic
        """
        is_multimodal = model and model.model_use == "multimodal"
        formatted_messages = []

        for message in messages:
            formatted_message = self._dispatch(
                "format_message",
                record=message,
                is_multimodal=is_multimodal,
            )
            if formatted_message:
                formatted_messages.append(formatted_message)

        formatted_messages = self._anthropic_merge_consecutive_user_messages(
            formatted_messages,
        )

        return formatted_messages

    def _anthropic_merge_consecutive_user_messages(self, messages):
        """Merge consecutive user messages as required by Anthropic API.

        Anthropic requires alternating user/assistant messages.
        """
        if not messages:
            return []

        merged = []
        for msg in messages:
            if merged and merged[-1]["role"] == msg["role"] == "user":
                prev_content = merged[-1]["content"]
                curr_content = msg["content"]

                if isinstance(prev_content, str) and isinstance(curr_content, str):
                    merged[-1]["content"] = prev_content + "\n" + curr_content
                elif isinstance(prev_content, list) and isinstance(curr_content, list):
                    merged[-1]["content"] = prev_content + curr_content
                elif isinstance(prev_content, str) and isinstance(curr_content, list):
                    merged[-1]["content"] = [
                        {"type": "text", "text": prev_content},
                    ] + curr_content
                elif isinstance(prev_content, list) and isinstance(curr_content, str):
                    merged[-1]["content"] = prev_content + [
                        {"type": "text", "text": curr_content},
                    ]
            else:
                merged.append(msg)

        return merged

    def anthropic_models(self, model_id=None):
        """List available Anthropic models.

        Args:
            model_id: Optional specific model ID to retrieve

        Yields:
            dict: Model data with name and details
        """
        if model_id:
            model = self.client.models.retrieve(model_id)
            yield self._anthropic_parse_model(model)
        else:
            response = self.client.models.list()
            for model in response.data:
                yield self._anthropic_parse_model(model)

    def _anthropic_parse_model(self, model):
        """Parse Anthropic model into Odoo format.

        Args:
            model: Anthropic model object

        Returns:
            dict: {"name": str, "details": dict}
        """
        capabilities = ["chat"]

        model_id = model.id.lower()
        if "opus" in model_id or "claude-3" in model_id or "claude-4" in model_id:
            capabilities.append("multimodal")

        return {
            "name": model.id,
            "details": {
                "id": model.id,
                "display_name": getattr(model, "display_name", model.id),
                "capabilities": capabilities,
                "created_at": str(getattr(model, "created_at", "")),
            },
        }

    def _determine_model_use(self, name, capabilities):
        """Override to handle Anthropic-specific model classification."""
        if self.service != "anthropic":
            return super()._determine_model_use(name, capabilities)

        if any(cap in capabilities for cap in ["multimodal", "vision"]):
            return "multimodal"

        return "chat"
