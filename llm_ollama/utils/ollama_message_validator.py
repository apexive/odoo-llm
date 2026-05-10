import logging

from ..utils.ollama_tool_call_id_utils import OllamaToolCallIdUtils

_logger = logging.getLogger(__name__)


class OllamaMessageValidator:
    """
    A dedicated class for validating and cleaning message structures
    for Ollama API compatibility.

    This validator ensures that:
    1. All tool messages have a corresponding assistant message with matching tool_calls
    2. All assistant messages with tool_calls have corresponding tool responses
    3. Tool messages followed by user messages are removed
    4. Tool calls from assistant messages followed by user messages are removed

    Usage:
        validator = OllamaMessageValidator(messages)
        cleaned_messages = validator.validate_and_clean()
    """

    def __init__(self, messages):
        """
        Initialize the message validator.

        Args:
            messages (list): List of message dictionaries to validate
        """
        self.messages = messages.copy()
        self.tool_call_map = {}  # Maps tool call IDs to their assistant messages
        self.tool_response_map = {}  # Maps tool names to their responses

    def validate_and_clean(self):
        """
        Main validation method that orchestrates the validation process.

        Returns:
            list: Cleaned list of messages with invalid entries removed
        """
        if not self.messages:
            return self.messages

        # Log original messages
        _logger.debug("=== ORIGINAL MESSAGES BEFORE VALIDATION ===")
        for i, msg in enumerate(self.messages):
            role = msg.get("role", "unknown")
            content_preview = (
                (msg.get("content", "")[:30] + "...") if msg.get("content") else "None"
            )

            if role == "tool":
                _logger.debug(
                    f"Message {i} - Role: {role}, Tool Name: {msg.get('name', 'none')}, Content: {content_preview}"
                )
            elif role == "assistant" and msg.get("tool_calls"):
                tool_call_ids = [
                    tc.get("id", "unknown") for tc in msg.get("tool_calls", [])
                ]
                _logger.debug(
                    f"Message {i} - Role: {role}, Tool Calls: {tool_call_ids}, Content: {content_preview}"
                )
            else:
                _logger.debug(f"Message {i} - Role: {role}, Content: {content_preview}")

        # Build maps for validation
        self.build_message_maps()

        # Perform validation and cleaning
        self.remove_orphaned_tool_messages()
        self.handle_missing_tool_responses()
        self.remove_tool_calls_from_non_final_assistant_messages()

        # Filter out None entries (removed messages)
        cleaned_messages = [msg for msg in self.messages if msg is not None]

        _logger.debug(
            f"Validation complete. Original messages: {len(self.messages)}, Cleaned messages: {len(cleaned_messages)}"
        )

        return cleaned_messages

    def build_message_maps(self):
        """
        Build mappings between tool calls and their responses.

        This creates two maps:
        1. tool_call_map: Maps tool call IDs to their info
        2. tool_response_map: Maps tool names to their responses
        """
        # First pass: collect all tool calls from assistant messages
        for i, msg in enumerate(self.messages):
            if msg and msg.get("role") == "assistant" and msg.get("tool_calls"):
                for tool_call in msg.get("tool_calls", []):
                    tool_id = tool_call.get("id")
                    if tool_id:
                        self.tool_call_map[tool_id] = {
                            "index": i,
                            "message": msg,
                            "tool_call": tool_call,
                        }

        # Second pass: collect all tool responses - now parse from content/body
        for i, msg in enumerate(self.messages):
            if msg and msg.get("role") == "tool":
                tool_name = msg.get("name")
                if not tool_name:
                    # Try to extract from content if it's JSON
                    try:
                        import json

                        content = msg.get("content", "")
                        if content:
                            tool_data = json.loads(content)
                            if tool_data.get("type") == "tool_execution":
                                tool_name = tool_data.get("tool_name")
                    except (json.JSONDecodeError, TypeError):
                        pass

                if tool_name:
                    self.tool_response_map[tool_name] = {"index": i, "message": msg}

    def remove_orphaned_tool_messages(self):  # noqa: C901
        """
        Remove tool messages that don't have matching tool calls or are followed by
        user messages (but preserve tool messages followed by assistant messages).
        """
        # First, remove tool messages without matching tool calls
        for i, msg in enumerate(self.messages):
            if not msg or msg.get("role") != "tool":
                continue

            tool_name = msg.get("name")
            if not tool_name:
                # Try to extract from content if it's JSON
                try:
                    import json

                    content = msg.get("content", "")
                    if content:
                        tool_data = json.loads(content)
                        if tool_data.get("type") == "tool_execution":
                            tool_name = tool_data.get("tool_name")
                except (json.JSONDecodeError, TypeError):
                    pass

            if not tool_name:
                # Remove tool messages without tool names
                self.messages[i] = None
                continue

            # Check if this tool name matches any function name in tool calls using all strategies
            found_match = False

            # Strategy 1: Direct function name matching
            for _, info in self.tool_call_map.items():
                if info["tool_call"]["function"]["name"] == tool_name:
                    found_match = True
                    break

            # Strategy 2: Check if tool name is encoded in any tool_call_id
            if not found_match:
                for tool_id in self.tool_call_map.keys():
                    extracted_tool_name = (
                        OllamaToolCallIdUtils.extract_tool_name_from_id(tool_id)
                    )
                    if extracted_tool_name and extracted_tool_name == tool_name:
                        found_match = True
                        break

                # Strategy 3: Substring matching as fallback
                if not found_match:
                    for tool_id in self.tool_call_map.keys():
                        if tool_name in tool_id:
                            found_match = True
                            break

            if not found_match:
                self.messages[i] = None

        # Next, check for tool messages followed by user messages ONLY
        # (preserve tool messages followed by assistant messages)
        for i, msg in enumerate(self.messages):
            if not msg or msg.get("role") != "tool":
                continue

            # Check if this tool message is followed by user messages
            for j in range(i + 1, len(self.messages)):
                next_msg = self.messages[j]
                if next_msg and next_msg.get("role") == "user":
                    _logger.info(
                        f"Removing tool message at position {i} because it's followed by a user message"
                    )
                    self.messages[i] = None
                    break

    def handle_missing_tool_responses(self):
        """
        Handle tool calls that don't have corresponding tool responses.

        This method:
        1. Identifies tool calls without responses
        2. Removes those tool calls from assistant messages
        """
        # Find tool_calls without responses
        missing_responses = []
        for tool_call_id, info in self.tool_call_map.items():
            tool_call = info["tool_call"]
            function_name = tool_call.get("function", {}).get("name")

            # Check if this tool call has a matching response using our three strategies
            has_response = False

            # Strategy 1: Match by function name
            if function_name in self.tool_response_map:
                has_response = True

            # Strategy 2: Match by extracted tool name from tool_call_id
            if not has_response:
                extracted_tool_name = OllamaToolCallIdUtils.extract_tool_name_from_id(
                    tool_call_id
                )
                if (
                    extracted_tool_name
                    and extracted_tool_name in self.tool_response_map
                ):
                    has_response = True

            # Strategy 3: Match by substring
            if not has_response:
                for tool_name in self.tool_response_map.keys():
                    if tool_name in tool_call_id:
                        has_response = True
                        break

            # If no response found with any strategy, add to missing responses
            if not has_response:
                missing_responses.append(tool_call_id)
                _logger.warning(f"Tool call {tool_call_id} has no matching response")

        if missing_responses:
            _logger.warning(
                f"Found {len(missing_responses)} tool calls without responses"
            )

            # Process each assistant message to remove tool calls without responses
            for msg_index, msg in enumerate(self.messages):
                if msg and msg.get("role") == "assistant" and msg.get("tool_calls"):
                    # Filter out tool_calls without responses
                    updated_tool_calls = [
                        tc
                        for tc in msg.get("tool_calls", [])
                        if tc.get("id") not in missing_responses
                    ]

                    if updated_tool_calls:
                        # Keep the message but with only the tool_calls that have responses
                        self.messages[msg_index] = {
                            "role": "assistant",
                            "content": msg.get("content")
                            or "",  # Ensure content is never null
                            "tool_calls": updated_tool_calls,
                        }
                    else:
                        # If no tool_calls remain, remove them entirely
                        self.messages[msg_index] = {
                            "role": "assistant",
                            "content": msg.get("content")
                            or "",  # Ensure content is never null
                        }

    def remove_tool_calls_from_non_final_assistant_messages(self):
        """
        Remove tool calls from assistant messages that are followed by user messages.

        This preserves tool calls in assistant messages that are followed by other assistant
        messages or tool messages, but removes them when followed by user messages to prevent
        the LLM from seeing tool calls that have already been processed in a new conversation turn.
        """
        # Find assistant messages with tool calls that are followed by user messages
        for i, msg in enumerate(self.messages):
            if not msg or i >= len(self.messages) - 1:  # Skip None or last message
                continue

            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                # Check if this assistant message is followed by a user message
                has_following_user_message = False
                for j in range(i + 1, len(self.messages)):
                    if (
                        self.messages[j] is not None
                        and self.messages[j].get("role") == "user"
                    ):
                        has_following_user_message = True
                        break

                if has_following_user_message:
                    # Remove tool calls from this assistant message
                    _logger.info(
                        f"Removing tool calls from assistant message at position {i} because it's followed by a user message"
                    )
                    self.messages[i] = {
                        "role": "assistant",
                        "content": msg.get("content")
                        or "",  # Ensure content is never null
                    }
