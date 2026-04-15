import json
import logging
import time

from anthropic import Anthropic, APIStatusError

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Retry configuration for transient Anthropic API errors (e.g. overloaded_error)
_RETRY_STATUS_CODES = {529}          # 529 = overloaded
_RETRY_ERROR_TYPES = {"overloaded_error"}
_MAX_RETRIES = 4
_RETRY_BASE_DELAY = 2.0              # seconds — doubles each attempt: 2, 4, 8, 16


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
            params["system"] = [
                {
                    "type": "text",
                    "text": system_content,
                    "cache_control": {"type": "ephemeral"},
                }
            ]

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

    # =========================================================================
    # RETRY LOGIC
    # =========================================================================

    def _anthropic_is_retryable(self, exc):
        """Return True if the exception is a transient Anthropic error worth retrying.

        Retryable conditions:
        - HTTP 529 (overloaded_error): Anthropic servers temporarily at capacity
        - HTTP 529 is the canonical status for overload; the SDK raises APIStatusError
        """
        if isinstance(exc, APIStatusError):
            if exc.status_code in _RETRY_STATUS_CODES:
                return True
            body = getattr(exc, "body", {}) or {}
            error_type = (body.get("error") or {}).get("type", "")
            if error_type in _RETRY_ERROR_TYPES:
                return True
        return False

    def _anthropic_call_with_retry(self, fn, *args, **kwargs):
        """Call fn(*args, **kwargs) with exponential backoff on retryable errors.

        Retries up to _MAX_RETRIES times with delays of 2, 4, 8, 16 seconds.
        Non-retryable errors are re-raised immediately without any delay.

        Args:
            fn: Callable to invoke (e.g. self.client.messages.create)
            *args / **kwargs: Forwarded to fn

        Returns:
            Whatever fn returns on success

        Raises:
            The last exception if all retries are exhausted, or the original
            exception immediately if it is not retryable.
        """
        last_exc = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                return fn(*args, **kwargs)
            except Exception as exc:
                if not self._anthropic_is_retryable(exc):
                    raise
                last_exc = exc
                if attempt < _MAX_RETRIES:
                    delay = _RETRY_BASE_DELAY * (2 ** attempt)
                    _logger.warning(
                        "Anthropic overloaded (attempt %d/%d) — retrying in %.0fs: %s",
                        attempt + 1,
                        _MAX_RETRIES,
                        delay,
                        exc,
                    )
                    time.sleep(delay)
                else:
                    _logger.error(
                        "Anthropic still overloaded after %d retries — giving up: %s",
                        _MAX_RETRIES,
                        exc,
                    )
        raise last_exc

    # =========================================================================
    # RESPONSE HANDLERS
    # =========================================================================

    def _anthropic_process_response(self, params):
        """Process non-streaming response from Anthropic.

        Returns:
            dict: {"content": str} and/or {"tool_calls": list} and/or {"thinking": str}
        """
        response = self._anthropic_call_with_retry(
            self.client.messages.create, **params
        )
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

        Retries on overloaded_error before opening the stream.  Once the
        stream is open we do not retry mid-stream (partial output would be
        lost), so the retry only wraps the initial connection attempt.

        Yields:
            dict: {"content": str} or {"tool_calls": list} or {"thinking": str}
        """
        # Retry only the stream *open* — use a lambda so we get a fresh context mgr
        stream_ctx = self._anthropic_call_with_retry(
            lambda: self.client.messages.stream(**params)
        )

        with stream_ctx as stream:
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

        # Find the ID of the last user message so we can strip images from older ones
        last_user_msg_id = None
        if is_multimodal:
            for message in reversed(list(messages)):
                if message.is_llm_user_message()[message]:
                    last_user_msg_id = message.id
                    break

        for message in messages:
            is_latest_user = (
                is_multimodal
                and message.is_llm_user_message()[message]
                and message.id == last_user_msg_id
            )
            formatted_message = self._dispatch(
                "format_message",
                record=message,
                is_multimodal=is_multimodal,
                is_latest_user_message=is_latest_user,
            )
            if formatted_message:
                formatted_messages.append(formatted_message)

        formatted_messages = self._anthropic_merge_consecutive_user_messages(
            formatted_messages,
        )

        return formatted_messages

    def _content_has_tool_result(self, content):
        """Check if message content contains tool_result blocks.

        Anthropic requires that tool_result blocks are never merged with plain
        text or other content in the same user message — doing so breaks the
        strict tool_use ↔ tool_result pairing and causes HTTP 400 errors.

        Args:
            content: Message content (str or list of content blocks)

        Returns:
            bool: True if content contains any tool_result block
        """
        if isinstance(content, list):
            return any(
                isinstance(block, dict) and block.get("type") == "tool_result"
                for block in content
            )
        return False

    def _anthropic_merge_consecutive_user_messages(self, messages):
        """Merge consecutive user messages as required by Anthropic API.

        Anthropic requires strictly alternating user/assistant turns.

        IMPORTANT — tool_result isolation rule:
        A tool_result block must appear in a user message that immediately
        follows the assistant message containing the matching tool_use block.
        If we merge a tool_result user message with the next plain-text user
        message, Anthropic sees the tool_use_id in a context where there is
        no preceding tool_use, and returns:
            HTTP 400 "unexpected tool_use_id found in tool_result blocks"

        Fix: never merge any message that contains (or would receive)
        tool_result blocks — keep them as separate user turns.
        """
        if not messages:
            return []

        merged = []
        for msg in messages:
            if merged and merged[-1]["role"] == msg["role"] == "user":
                prev_content = merged[-1]["content"]
                curr_content = msg["content"]

                # Never merge when either side carries tool_result blocks
                if self._content_has_tool_result(prev_content) or \
                        self._content_has_tool_result(curr_content):
                    merged.append(msg)
                    continue

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
