import logging

_logger = logging.getLogger(__name__)


class OpenAIMessageValidator:
    """
    A dedicated class for validating and cleaning message structures
    for OpenAI API compatibility.

    This validator ensures that:
    1. All tool messages have a corresponding assistant message with matching tool_calls
    2. All assistant messages with tool_calls have corresponding tool responses
    3. The message structure is valid and consistent for the OpenAI API

    Usage:
        validator = OpenAIMessageValidator(messages)
        cleaned_messages = validator.validate_and_clean()
    """

    def __init__(self, messages, logger=None, verbose_logging=False):
        """
        Initialize the message validator.

        Args:
            messages (list): List of message dictionaries to validate
            logger (Logger, optional): Custom logger instance
            verbose_logging (bool): Whether to enable verbose logging
        """
        self.messages = messages
        self.logger = logger or logging.getLogger(__name__)
        self.verbose_logging = verbose_logging
        self.tool_call_map = {}  # Maps tool_call_ids to their assistant messages
        self.tool_response_map = {}  # Maps tool_call_ids to their tool response messages

    def validate_and_clean(self):
        """
        Main validation method that orchestrates the validation process.

        Returns:
            list: Cleaned list of messages with invalid entries removed
        """
        if not self.messages:
            return self.messages
        self.messages = [msg for msg in self.messages if self._is_valid_message(msg)]
        if self.verbose_logging:
            self.log_message_details()

        self.build_message_maps()
        self.remove_orphaned_tool_messages()
        self.handle_missing_tool_responses()
        self._remove_intervening_user_messages()

        # Remove any messages marked for removal (now includes intervening user messages)
        cleaned_messages = [msg for msg in self.messages if msg is not None]

        if self.verbose_logging:
            self.logger.info(
                f"Validation complete. Original messages: {len(self.messages)}, "
                f"Cleaned messages: {len(cleaned_messages)}"
            )

        return cleaned_messages

    def log_message_details(self):
        """Log details about each message for debugging"""
        self.logger.info(f"Validating {len(self.messages)} messages")
        for i, msg in enumerate(self.messages):
            role = msg.get("role", "unknown")
            tool_call_id = msg.get("tool_call_id", "none")
            tool_calls = msg.get("tool_calls", [])
            self.logger.info(
                f"Message {i} - Role: {role}, Tool Call ID: {tool_call_id}, "
                f"Tool Calls: {len(tool_calls)}"
            )

    def build_message_maps(self):
        """
        Build maps connecting tool calls to their responses.

        This creates two mappings:
        1. tool_call_map: Maps tool_call_ids to their originating assistant messages
        2. tool_response_map: Maps tool_call_ids to their tool response messages
        """
        # Map assistant messages with their tool_call_ids
        for i, msg in enumerate(self.messages):
            if not msg:
                continue

            # Process assistant messages with tool calls
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                for tool_call in msg.get("tool_calls", []):
                    tool_call_id = tool_call.get("id")
                    if tool_call_id:
                        self.tool_call_map[tool_call_id] = {
                            "index": i,
                            "tool_call": tool_call,
                            "message": msg,
                        }
                        if self.verbose_logging:
                            self.logger.info(
                                f"Found tool_call_id in assistant message: {tool_call_id}"
                            )

            # Process tool response messages - now parse from content/body
            if msg.get("role") == "tool":
                tool_call_id = msg.get("tool_call_id")
                if not tool_call_id:
                    # Try to extract from content if it's JSON
                    try:
                        import json

                        content = msg.get("content", "")
                        if content:
                            tool_data = json.loads(content)
                            if tool_data.get("type") == "tool_execution":
                                tool_call_id = tool_data.get("tool_call_id")
                    except (json.JSONDecodeError, TypeError):
                        pass

                if tool_call_id:
                    self.tool_response_map[tool_call_id] = {"index": i, "message": msg}
                    if self.verbose_logging:
                        self.logger.info(
                            f"Found tool response for tool_call_id: {tool_call_id}"
                        )

    def remove_orphaned_tool_messages(self):
        """
        Remove tool messages that don't have a matching assistant message with tool_calls.
        Also removes duplicate tool messages with the same tool_call_id.

        This ensures that every tool message corresponds to a valid tool call from an assistant.
        """
        seen_tool_call_ids = set()

        for i, msg in enumerate(self.messages):
            if not msg:
                continue

            if msg.get("role") == "tool":
                tool_call_id = msg.get("tool_call_id")
                if not tool_call_id:
                    # Try to extract from content if it's JSON
                    try:
                        import json

                        content = msg.get("content", "")
                        if content:
                            tool_data = json.loads(content)
                            if tool_data.get("type") == "tool_execution":
                                tool_call_id = tool_data.get("tool_call_id")
                    except (json.JSONDecodeError, TypeError):
                        pass

                if tool_call_id and tool_call_id not in self.tool_call_map:
                    self.logger.warning(
                        f"Removing tool message with ID {tool_call_id} because it has no "
                        f"matching assistant message with tool_calls"
                    )
                    self.messages[i] = None
                elif not tool_call_id:
                    self.logger.warning(
                        f"Removing tool message at index {i} because it has no tool_call_id"
                    )
                    self.messages[i] = None
                elif tool_call_id in seen_tool_call_ids:
                    # This is a duplicate tool message for the same tool_call_id
                    self.logger.warning(
                        f"Removing duplicate tool message at index {i} with ID {tool_call_id} "
                        f"(already have a tool response for this ID)"
                    )
                    self.messages[i] = None
                else:
                    # Check if tool message comes after its assistant message
                    assistant_index = self.tool_call_map.get(tool_call_id, {}).get(
                        "index", -1
                    )
                    if assistant_index >= 0 and i < assistant_index:
                        self.logger.warning(
                            f"Removing tool message at index {i} with ID {tool_call_id} because it appears "
                            f"BEFORE its assistant message at index {assistant_index}"
                        )
                        self.messages[i] = None
                    else:
                        # Mark this tool_call_id as seen and keep the message
                        seen_tool_call_ids.add(tool_call_id)
                        if self.verbose_logging:
                            self.logger.info(
                                f"Keeping tool message at index {i} with ID {tool_call_id} "
                                f"(found matching assistant message at index {assistant_index})"
                            )

    def handle_missing_tool_responses(self):
        """
        Handle cases where assistant messages have tool_calls without corresponding tool responses.

        This either removes the orphaned tool_calls or updates the assistant message to remove them.
        """
        # Find tool_calls without responses
        missing_responses = set(self.tool_call_map.keys()) - set(
            self.tool_response_map.keys()
        )

        if missing_responses:
            self.logger.warning(
                f"Found {len(missing_responses)} tool_calls without responses: {missing_responses}"
            )

            # Process each assistant message with tool_calls
            for tool_call_id, info in self.tool_call_map.items():
                if tool_call_id in missing_responses:
                    msg_index = info["index"]
                    msg = self.messages[msg_index]

                    # Filter out tool_calls without responses
                    updated_tool_calls = [
                        tc
                        for tc in msg.get("tool_calls", [])
                        if tc.get("id") not in missing_responses
                    ]

                    if updated_tool_calls:
                        # Keep the message but with only the tool_calls that have responses
                        self.messages[msg_index]["tool_calls"] = updated_tool_calls
                        if self.verbose_logging:
                            self.logger.info(
                                f"Updated assistant message {msg_index} to only include "
                                f"tool_calls with responses"
                            )
                    else:
                        # If no tool_calls remain, remove them entirely
                        self.messages[msg_index] = {
                            "role": "assistant",
                            "content": msg.get("content")
                            or "",  # Ensure content is never null
                        }
                        if self.verbose_logging:
                            self.logger.info(
                                f"Removed all tool_calls from assistant message {msg_index}"
                            )

    def _remove_intervening_user_messages(self):
        """
        Remove user messages that appear between an assistant message with tool_calls
        and its required tool response messages.
        """
        indices_to_remove = set()
        i = 0
        while i < len(self.messages):
            msg = self.messages[i]
            if not msg:
                i += 1
                continue

            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                expected_tool_ids = {
                    tc.get("id") for tc in msg["tool_calls"] if tc.get("id")
                }
                found_tool_ids = set()
                j = i + 1

                # Look ahead for expected tool responses or intervening user messages
                while j < len(self.messages) and len(found_tool_ids) < len(
                    expected_tool_ids
                ):
                    next_msg = self.messages[j]
                    if not next_msg:
                        j += 1
                        continue  # Skip already removed messages

                    if next_msg.get("role") == "tool":
                        tool_call_id = next_msg.get("tool_call_id")
                        if tool_call_id in expected_tool_ids:
                            found_tool_ids.add(tool_call_id)
                        else:
                            # This tool response doesn't belong here, might be handled
                            # by remove_orphaned_tool_messages later, but stop looking ahead here.
                            break
                    elif next_msg.get("role") == "user":
                        # Found an intervening user message BEFORE all tool responses were found
                        self.logger.warning(
                            f"Removing intervening user message at index {j} found after "
                            f"assistant tool_calls at index {i}"
                        )
                        indices_to_remove.add(j)
                        # Continue checking subsequent messages in case more user messages intervened
                    elif next_msg.get("role") == "assistant":
                        # Another assistant message appeared before tool responses, stop looking ahead
                        break
                    # Ignore other message types for this specific check

                    j += 1
                # Move main loop counter past the block we just examined
                i = j
            else:
                i += 1

        # Mark messages for removal
        for index in indices_to_remove:
            self.messages[index] = None

    def _is_valid_message(self, msg):
        """
        Check if a message is valid (has required fields and content).

        Args:
            msg (dict): Message to validate

        Returns:
            bool: True if message is valid, False otherwise
        """
        if not msg:
            return False

        # Check if message has a role
        if "role" not in msg:
            self.logger.warning("Message missing 'role' field")
            return False

        # Special case for tool messages which might have empty content but valid tool_call_id
        if msg["role"] == "tool" and msg.get("tool_call_id"):
            return True

        # Special case for assistant messages with tool_calls but no content
        if msg["role"] == "assistant" and msg.get("tool_calls"):
            # Assistant messages with tool_calls are valid even without content
            return True

        # Check if message has content (can be string or dict)
        if "content" not in msg:
            self.logger.warning(
                f"Message with role '{msg['role']}' missing 'content' field"
            )
            return False

        # Check if content is empty
        content = msg["content"]
        if (
            content is None
            or (isinstance(content, str) and not content)
            or (isinstance(content, list) and not content)
        ):
            self.logger.warning(f"Message with role '{msg['role']}' has empty content")
            return False

        return True
