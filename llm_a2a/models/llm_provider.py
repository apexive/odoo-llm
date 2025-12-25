import logging

from odoo import models

_logger = logging.getLogger(__name__)

# Module-level storage for A2A tools (thread-safe via Odoo's request handling)
_current_a2a_tools = {}


class LlmProviderA2a(models.Model):
    """Extend llm.provider to support A2A tool definitions."""

    _inherit = "llm.provider"

    def chat(
        self,
        messages,
        model=None,
        stream=False,
        tools=None,
        prepend_messages=None,
        **kwargs,
    ):
        """Override chat to handle A2A tools from kwargs.

        A2A tools are passed via kwargs['a2a_tools'] and stored temporarily
        for format_tools to access.
        """
        # Extract a2a_tools from kwargs
        a2a_tools = kwargs.pop("a2a_tools", None)

        if a2a_tools:
            _logger.info("Storing %d A2A tools for provider %s", len(a2a_tools), self.id)
            # Store in module-level dict keyed by provider id
            _current_a2a_tools[self.id] = a2a_tools

        try:
            return super().chat(
                messages,
                model=model,
                stream=stream,
                tools=tools,
                prepend_messages=prepend_messages,
                **kwargs,
            )
        finally:
            # Clean up after chat completes
            if self.id in _current_a2a_tools:
                del _current_a2a_tools[self.id]

    def openai_chat(
        self,
        messages,
        model=None,
        stream=False,
        tools=None,
        prepend_messages=None,
        **kwargs,
    ):
        """Override OpenAI chat to ensure A2A tools are included even when no regular tools.

        The original openai_chat only calls format_tools when tools is not empty.
        We need to call it regardless to include A2A tools.
        """
        model = self.get_model(model, "chat")

        # Format mail.message records for OpenAI
        formatted_messages = self.format_messages(messages)

        # Prepend messages (system prompts, etc.) if provided
        if prepend_messages:
            formatted_messages = prepend_messages + formatted_messages

        # Build params
        params = {
            "model": model.name,
            "stream": stream,
            "messages": formatted_messages,
        }

        # ALWAYS call format_tools to include A2A tools (even if tools is empty)
        formatted_tools = self.format_tools(tools)
        if formatted_tools:
            params["tools"] = formatted_tools
            params["tool_choice"] = kwargs.get("tool_choice", "auto")

        # Make the API call
        response = self.client.chat.completions.create(**params)

        # Process the response based on streaming mode
        if not stream:
            return self._openai_process_non_streaming_response(response)
        else:
            return self._openai_process_streaming_response(response)

    def format_tools(self, tools):
        """Override to merge A2A tools with regular Odoo tools.

        A2A tools are retrieved from module-level storage (set by chat method).
        This method wraps the dispatch call and appends A2A tools after.

        Args:
            tools: llm.tool recordset of regular tools

        Returns:
            List of formatted tools for the provider
        """
        # Let the service-specific format_tools handle regular tools
        # We call _dispatch directly to avoid infinite recursion
        formatted = self._dispatch("format_tools", tools) if tools else []

        # Get A2A tools from module-level storage
        a2a_tools = _current_a2a_tools.get(self.id, [])

        if a2a_tools:
            for a2a_tool in a2a_tools:
                formatted_a2a = self._format_a2a_tool_for_service(a2a_tool)
                if formatted_a2a:
                    formatted.append(formatted_a2a)
                    _logger.info("Added A2A tool to formatted list: %s", a2a_tool.get("name"))

            _logger.info(
                "Total formatted tools: %d (including %d A2A tools)",
                len(formatted),
                len(a2a_tools),
            )

        return formatted

    def _format_a2a_tool_for_service(self, a2a_tool):
        """Format a single A2A tool definition based on the current provider service.

        A2A tools already come in a standard format:
        {
            "name": "delegate_to_xxx",
            "description": "...",
            "inputSchema": {
                "type": "object",
                "properties": {...},
                "required": [...]
            }
        }

        We transform it to match the provider's expected format.
        """
        if not a2a_tool:
            return None

        input_schema = a2a_tool.get("inputSchema", {})
        name = a2a_tool.get("name", "")
        description = a2a_tool.get("description", "")

        # Format based on provider service
        if self.service == "anthropic":
            # Anthropic format: input_schema
            return {
                "name": name,
                "description": description,
                "input_schema": {
                    "type": "object",
                    "properties": input_schema.get("properties", {}),
                    "required": input_schema.get("required", []),
                },
            }
        elif self.service == "openai":
            # OpenAI format: function with parameters
            return {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": {
                        "type": "object",
                        "properties": input_schema.get("properties", {}),
                        "required": input_schema.get("required", []),
                    },
                },
            }
        else:
            # Generic format (similar to Anthropic)
            return {
                "name": name,
                "description": description,
                "input_schema": {
                    "type": "object",
                    "properties": input_schema.get("properties", {}),
                    "required": input_schema.get("required", []),
                },
            }
