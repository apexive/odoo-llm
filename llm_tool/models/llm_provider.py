import json
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class LLMProvider(models.Model):
    _inherit = "llm.provider"

    @api.model
    def _is_tool_call_complete(self, function_data, expected_endings=("]", "}")):
        """Check if a tool call is complete (utility function for providers).

        Args:
            function_data: Dictionary with 'name' and 'arguments' keys
            expected_endings: Tuple of valid JSON ending characters

        Returns:
            bool: True if the tool call appears complete
        """
        tool_name = function_data.get("name")
        args_str = function_data.get("arguments", "").strip()

        if not tool_name or not args_str:
            return False

        try:
            json.loads(args_str)
            if args_str.endswith(expected_endings):
                return True
        except json.JSONDecodeError:
            pass

        return False

    def _prepare_prepend_messages(self, prepend_messages, tools):
        """Inject tool consent instructions into prepend messages.

        Overrides the base hook to add consent instructions for tools
        that require user consent before execution.

        Args:
            prepend_messages: List of pre-formatted message dicts
            tools: llm.tool recordset of available tools

        Returns:
            List of message dicts with consent instructions injected
        """
        prepend_messages = super()._prepare_prepend_messages(prepend_messages, tools)

        if not tools:
            return prepend_messages

        consent_required = tools.filtered(lambda t: t.requires_user_consent)
        if not consent_required:
            return prepend_messages

        return self._inject_tool_consent(prepend_messages, consent_required)

    def _inject_tool_consent(self, prepend_messages, consent_tools):
        """Add consent instructions to prepend messages.

        Args:
            prepend_messages: List of message dicts to modify
            consent_tools: llm.tool recordset of tools requiring consent

        Returns:
            List of message dicts with consent instructions added
        """
        tool_names = ", ".join([f"'{t.name}'" for t in consent_tools])
        config = self.env["llm.tool.consent.config"].get_active_config()
        consent_instruction = config.system_message_template.format(
            tool_names=tool_names
        )

        # Make a copy to avoid modifying the original
        prepend_messages = list(prepend_messages or [])

        # Find existing system message and append consent instructions
        for msg in prepend_messages:
            if msg.get("role") == "system":
                content = msg.get("content", "")

                # Handle list format - modify in place (preserves format)
                if (
                    isinstance(content, list)
                    and content
                    and isinstance(content[0], dict)
                ):
                    existing_text = self._extract_content_text(content)
                    separator = "\n\n" if existing_text else ""
                    content[0]["text"] = (
                        f"{existing_text}{separator}{consent_instruction}"
                    )
                else:
                    # String format
                    existing_text = self._extract_content_text(content)
                    separator = "\n\n" if existing_text else ""
                    msg["content"] = f"{existing_text}{separator}{consent_instruction}"

                return prepend_messages

        # No system message found, insert one at the beginning
        prepend_messages.insert(
            0,
            {
                "role": "system",
                "content": consent_instruction,
            },
        )

        return prepend_messages
