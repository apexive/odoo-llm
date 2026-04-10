import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class LLMThread(models.Model):
    _inherit = "llm.thread"

    assistant_id = fields.Many2one(
        "llm.assistant",
        string="Assistant",
        ondelete="restrict",
        help="The assistant used for this thread",
    )

    prompt_id = fields.Many2one(
        "llm.prompt",
        string="Prompt for workflow",
        ondelete="restrict",
        tracking=True,
        help="Prompt to use for workflow",
    )

    @api.onchange("assistant_id")
    def _onchange_assistant_id(self):
        """Update provider, model and tools when assistant changes"""
        if self.assistant_id:
            self.provider_id = self.assistant_id.provider_id
            self.model_id = self.assistant_id.model_id
            self.tool_ids = self.assistant_id.tool_ids
            self.prompt_id = self.assistant_id.prompt_id
        else:
            # Clear prompt when assistant is cleared
            self.prompt_id = False

    def set_assistant(self, assistant_id):
        """Set the assistant for this thread and update related fields

        Args:
            assistant_id (int): The ID of the assistant to set

        Returns:
            bool: True if successful, False otherwise
        """
        self.ensure_one()

        # If assistant_id is False or 0, clear the assistant and its prompt
        if not assistant_id:
            return self.write({"assistant_id": False, "prompt_id": False})

        # Get the assistant record
        assistant = self.env["llm.assistant"].browse(assistant_id)
        if not assistant.exists():
            return False

        # Update the thread with the assistant and related fields
        update_vals = {
            "assistant_id": assistant_id,
            "tool_ids": [(6, 0, assistant.tool_ids.ids)],
        }
        if assistant.provider_id.id:
            update_vals["provider_id"] = assistant.provider_id.id
        if assistant.model_id.id:
            update_vals["model_id"] = assistant.model_id.id
        if assistant.prompt_id.id:
            update_vals["prompt_id"] = assistant.prompt_id.id
        return self.write(update_vals)

    def action_open_thread(self):
        """Open the thread in the chat client interface

        Returns:
            dict: Action to open the thread in the chat client
        """
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "llm_thread.chat_client_action",
            "params": {
                "default_active_id": self.id,
            },
            "context": {
                "active_id": self.id,
            },
            "target": "current",
        }

    def get_context(self, base_context=None):
        """
        Get the context to pass to prompt rendering with thread-specific enhancements.
        This is the canonical method for creating prompt context in both production and testing.

        Args:
            base_context (dict): Additional context from caller (optional)

        Returns:
            dict: Context ready for prompt rendering
        """
        context = super().get_context(base_context or {})

        # If we have an assistant with default values, add them to the context
        if self.assistant_id:
            # Get assistant's evaluated default values using the current context
            assistant_defaults = self.assistant_id.get_evaluated_default_values(context)

            # Merge assistant defaults into context
            # Assistant defaults are added first, so thread context takes precedence
            if assistant_defaults:
                context = {**assistant_defaults, **context}

        return context

    @api.model
    def get_thread_by_id(self, thread_id):
        """Get a thread record by its ID

        Args:
            thread_id (int): ID of the thread

        Returns:
            tuple: (thread, error_response)
                  If successful, error_response will be None
                  If error, thread will be None
        """
        thread = self.browse(int(thread_id))
        if not thread.exists():
            return None, {"success": False, "error": "Thread not found"}
        return thread, None

    @api.model
    def get_thread_and_assistant(self, thread_id, assistant_id=False):
        """Get thread and assistant records by their IDs

        Args:
            thread_id (int): ID of the thread
            assistant_id (int, optional): ID of the assistant, or False to clear

        Returns:
            tuple: (thread, assistant, error_response)
                  If successful, error_response will be None
                  If error, thread and/or assistant will be None
        """
        # Get thread
        thread, error = self.get_thread_by_id(thread_id)
        if error:
            return None, None, error

        # If no assistant_id, return just the thread
        if not assistant_id:
            return thread, None, None

        # Get assistant from the assistant model
        assistant, error = self.env["llm.assistant"].get_assistant_by_id(assistant_id)
        if error:
            return thread, None, error

        return thread, assistant, None

    def _thread_to_store(self, store, **kwargs):
        """Extend base _thread_to_store to include assistant_id and prompt_id."""
        super()._thread_to_store(store, **kwargs)

        # Always add assistant_id and prompt_id to thread data (either value or False)
        for thread in self:
            thread_data = {
                "id": thread.id,
                "model": "llm.thread",
                "assistant_id": {
                    "id": thread.assistant_id.id,
                    "name": thread.assistant_id.name,
                    "model": "llm.assistant",
                }
                if thread.assistant_id
                else False,
                # prompt_id is defined in this module, so handle it here
                "prompt_id": {
                    "id": thread.prompt_id.id,
                    "name": thread.prompt_id.name,
                    "model": "llm.prompt",
                }
                if thread.prompt_id
                else False,
            }
            store.add("mail.thread", thread_data)

    def _extract_message_content(self, message):
        """Extract text content from a message regardless of format"""
        content = message.get("content", "")

        if isinstance(content, list) and len(content) > 0:
            return content[0].get("text", "")
        if isinstance(content, str):
            return content
        return ""

    def get_prepend_messages(self):
        """Hook: return a list of formatted messages to prepend to the conversation."""
        self.ensure_one()

        if self.prompt_id:
            try:
                # Get messages from the prompt with enhanced context
                return self.prompt_id.get_messages(self.get_context())
            except Exception as e:
                _logger.error(
                    "Error getting messages from prompt '%s': %s",
                    self.prompt_id.name,
                    e,
                )
                # Continue without prompt messages rather than failing completely
                # Post a user-friendly warning to the thread
                self.message_post(
                    body=_(
                        "Note: The prompt '%s' could not be loaded. "
                        "Continuing without it. (Error: %s)",
                    )
                    % (self.prompt_id.name, str(e)),
                )

        return []

    def generate_messages(self, last_message):
        """Generate messages with actual AI intelligence."""
        self.ensure_one()

        # Get last message if not provided
        if not last_message:
            try:
                last_message = self.get_latest_llm_message()
            except UserError:
                # No DB messages found - check if prepended messages have a user message
                prepend_msgs = self.get_prepend_messages()
                user_msg = next(
                    (msg for msg in prepend_msgs if msg.get("role") == "user"),
                    None,
                )

                if user_msg:
                    # Extract content from prepended user message
                    content = user_msg.get("content", [])
                    if isinstance(content, list) and content:
                        body = content[0].get("text", "")
                    else:
                        body = str(content)

                    # Create actual user message from prepended content
                    last_message = self.message_post(
                        body=body,
                        llm_role="user",
                        author_id=self.env.user.partner_id.id,
                    )
                else:
                    # No user message in prepended messages either
                    raise

        # Continue generation loop
        while self._should_continue(last_message):
            if last_message.llm_role in ("user", "tool"):
                if self.model_id.model_use in ("image_generation", "generation"):
                    last_message = yield from self._generate_response(last_message)
                elif self.model_id.model_use == "transcription":
                    last_message = yield from self._transcribe_response(last_message)
                else:
                    # Generate assistant response
                    last_message = yield from self._generate_assistant_response()
            elif last_message.llm_role == "assistant" and last_message.has_tool_calls():
                # Execute ALL tool calls from assistant message
                tool_calls = last_message.get_tool_calls()
                for tool_call in tool_calls:
                    tool_message = yield from self._execute_tool_call(
                        tool_call,
                        last_message,
                    )
                    last_message = tool_message
                    self.env.cr.commit()
            else:
                _logger.info(
                    f"Breaking loop. Last message role: {last_message.llm_role}, "
                    f"has_tool_calls: {last_message.has_tool_calls()}",
                )
                break

        return last_message

    def _generate_response(self, last_message):
        raise NotImplementedError

    def _transcribe_response(self, last_message):
        raise NotImplementedError

    def _generate_assistant_response(self):
        """Generate assistant response and handle tool calls.

        Catches LLM API errors and posts them as error messages in the thread
        so users can see what went wrong without checking server logs.
        """
        # Flush any pending writes to ensure latest messages are visible
        self.env.flush_all()

        # Use the new optimized method for LLM context
        message_history = self.get_llm_messages()

        # Determine if we should use streaming
        use_streaming = getattr(self.model_id, "supports_streaming", True)

        chat_kwargs = self._prepare_chat_kwargs(message_history, use_streaming)

        try:
            if use_streaming:
                # Handle streaming response - process tool calls directly from stream
                stream_response = self.sudo().model_id.chat(**chat_kwargs)
                assistant_message = yield from self._handle_streaming_response(
                    stream_response,
                )
            else:
                # Handle non-streaming response
                response = self.sudo().model_id.chat(**chat_kwargs)
                assistant_message = yield from self._handle_non_streaming_response(
                    response,
                )
        except Exception as e:
            # Post error message to thread so user can see it
            _logger.exception("LLM API error in thread %s", self.id)
            error_message, event = self._post_error_message(
                e,
                title=_("LLM API Error"),
            )
            yield event
            return error_message

        return assistant_message

    def _prepare_chat_kwargs(self, message_history, use_streaming):
        """Prepare chat kwargs for provider. Can be overridden by extensions."""
        return {
            "messages": message_history,
            "tools": self.tool_ids,
            "stream": use_streaming,
            "prepend_messages": self.get_prepend_messages(),
        }

    def get_llm_messages(self, limit=25):
        """Get the most recent LLM messages in chronological order.

        This method is optimized for LLM context preparation:
        - Always returns messages in chronological order (ASC)
        - Limits to the most recent N messages for context window management
        - Uses efficient database queries with proper indexing
        - Excludes error messages (is_error=True) from context
        - Sanitizes the window to remove orphaned tool_result blocks that
          would cause Anthropic HTTP 400 errors when their tool_use is
          outside the window (see _sanitize_message_window).

        Args:
            limit (int): Maximum number of recent messages to retrieve (default: 25)

        Returns:
            mail.message recordset: Recent LLM messages in chronological order
        """
        self.ensure_one()

        # Domain for filtering LLM messages only (excluding error messages)
        domain = [
            ("model", "=", self._name),
            ("res_id", "=", self.id),
            ("llm_role", "!=", False),  # Only messages with LLM roles
            ("is_error", "=", False),  # Exclude error messages from LLM context
        ]

        if limit:
            # Two-step approach for efficiency:
            # 1. Get the N most recent messages (DESC order)
            recent_messages = self.env["mail.message"].search(
                domain,
                order="create_date DESC, write_date DESC, id DESC",
                limit=limit,
            )
            # 2. Sort them chronologically for LLM context (ASC order)
            messages = recent_messages.sorted(
                lambda m: (m.create_date, m.write_date, m.id)
            )
        else:
            # If no limit, get all messages in chronological order
            messages = self.env["mail.message"].search(
                domain,
                order="create_date ASC, write_date ASC, id ASC",
            )

        return self._sanitize_message_window(messages)

    def _sanitize_message_window(self, messages):
        """Remove messages from the start of the window that would cause orphan errors.

        When the context window is limited (e.g. limit=25), the oldest fetched
        message might be a tool_result whose corresponding tool_use was cut off.
        Anthropic strictly requires every tool_result to have a preceding
        tool_use in the same request — sending an orphaned tool_result causes:
            HTTP 400 "unexpected tool_use_id found in tool_result blocks"

        Strategy:
        1. Collect all tool_use IDs present in assistant messages in the window.
        2. Collect all tool_result IDs present in tool messages in the window.
        3. Walk forward from the start, dropping:
           - tool messages whose tool_call_id has no matching tool_use in window
           - assistant messages at the very start whose tool_use blocks have no
             matching tool_result in window (incomplete cycle, would confuse API)
        4. Stop as soon as the first valid message is found.

        Args:
            messages: mail.message recordset in chronological order

        Returns:
            mail.message recordset with orphaned leading messages removed
        """
        if not messages:
            return messages

        # Build set of tool_use IDs present in assistant messages within window
        tool_use_ids_in_window = set()
        for msg in messages:
            if msg.llm_role == "assistant":
                for tc in (msg.body_json or {}).get("tool_calls", []):
                    if tc.get("id"):
                        tool_use_ids_in_window.add(tc["id"])

        # Build set of tool_result IDs present in tool messages within window
        tool_result_ids_in_window = set()
        for msg in messages:
            if msg.llm_role == "tool":
                tc_id = (msg.body_json or {}).get("tool_call_id")
                if tc_id:
                    tool_result_ids_in_window.add(tc_id)

        messages_list = list(messages)

        while messages_list:
            first = messages_list[0]

            # Drop tool messages whose tool_use was cut off by the window limit
            if first.llm_role == "tool":
                tc_id = (first.body_json or {}).get("tool_call_id")
                if tc_id and tc_id not in tool_use_ids_in_window:
                    _logger.debug(
                        "Dropping orphaned tool_result message %s "
                        "(tool_call_id %s has no matching tool_use in window)",
                        first.id,
                        tc_id,
                    )
                    messages_list.pop(0)
                    continue

            # Drop assistant messages at the start whose tool_use cycle is incomplete
            # (tool_use present but no tool_result in window → API would stall)
            if first.llm_role == "assistant":
                tool_calls = (first.body_json or {}).get("tool_calls", [])
                if tool_calls:
                    unresolved = [
                        tc for tc in tool_calls
                        if tc.get("id") not in tool_result_ids_in_window
                    ]
                    if unresolved:
                        _logger.debug(
                            "Dropping assistant message %s at window start: "
                            "%d tool_use block(s) have no tool_result in window",
                            first.id,
                            len(unresolved),
                        )
                        messages_list.pop(0)
                        continue

            # First message is clean — stop trimming
            break

        if not messages_list:
            return self.env["mail.message"]

        return self.env["mail.message"].browse([m.id for m in messages_list])

    def get_latest_llm_message(self):
        """Get the most recent LLM message for flow control.

        Returns:
            mail.message: The latest LLM message

        Raises:
            UserError: If no LLM messages exist
        """
        self.ensure_one()

        domain = [
            ("model", "=", self._name),
            ("res_id", "=", self.id),
            ("llm_role", "!=", False),
        ]

        result = self.env["mail.message"].search(
            domain,
            order="create_date DESC, write_date DESC, id DESC",
            limit=1,
        )

        if not result:
            raise UserError("No LLM messages found in this thread.")

        return result[0]

    def _should_continue(self, last_message):
        """Simplified continue logic based on message history."""
        if not last_message:
            return False

        # Continue if:
        # 1. Last message is user message → generate assistant response
        # 2. Last message is tool message → generate assistant response
        # 3. Last message is assistant with tool calls → execute tools
        if last_message.llm_role in ("user", "tool") or (
            last_message.llm_role == "assistant" and last_message.has_tool_calls()
        ):
            return True

        return False

    def _notify_bus(self, event_type, message):
        """Hook for subclasses to push bus notifications during generation.

        Called on each streaming event (message_create, message_chunk,
        message_update) so that server-side generation can update connected
        clients in real time without SSE.

        Override in subclasses to push bus notifications as needed.
        Default is a no-op so existing SSE-based flow is unaffected.

        Args:
            event_type (str): 'message_create', 'message_chunk', or 'message_update'
            message (mail.message): the message record being created/updated
        """
        pass

    def _handle_streaming_response(self, stream_response):
        """Handle streaming response from LLM provider with tool call processing."""
        message = None
        accumulated_content = ""
        collected_tool_calls = []

        for chunk in stream_response:
            # Initialize message on first content
            if message is None and chunk.get("content"):
                message = self.message_post(
                    body="Thinking...",
                    llm_role="assistant",
                    author_id=False,
                )
                self._notify_bus("message_create", message)
                yield {"type": "message_create", "message": message.to_store_format()}

            # Handle content streaming
            if chunk.get("content"):
                accumulated_content += chunk["content"]
                message.write({"body": self._process_llm_body(accumulated_content)})
                self._notify_bus("message_chunk", message)
                yield {"type": "message_chunk", "message": message.to_store_format()}

            # Collect tool calls for processing
            if chunk.get("tool_calls"):
                collected_tool_calls.extend(chunk["tool_calls"])
                _logger.debug(
                    f"Collected {len(chunk['tool_calls'])} tool calls from chunk",
                )

            # Handle errors
            if chunk.get("error"):
                yield {"type": "error", "error": chunk["error"]}
                return message

        # CRITICAL FIX: Create assistant message IMMEDIATELY if we have tool calls
        if collected_tool_calls:
            body_json = {"tool_calls": collected_tool_calls}

            if not message:
                message = self.message_post(
                    body="",  # Empty body for tool-only responses
                    body_json=body_json,
                    llm_role="assistant",
                    author_id=False,
                )
                self.env.cr.commit()
                self._notify_bus("message_create", message)
                yield {"type": "message_create", "message": message.to_store_format()}
            else:
                message.write({"body_json": body_json})
                self.env.cr.commit()
                self._notify_bus("message_update", message)
                yield {"type": "message_update", "message": message.to_store_format()}
        elif message and accumulated_content:
            message.write({"body": self._process_llm_body(accumulated_content)})
            self._notify_bus("message_update", message)
            yield {"type": "message_update", "message": message.to_store_format()}

        return message

    def _handle_non_streaming_response(self, response):
        """Handle non-streaming response from LLM provider."""
        # Extract content and tool calls from response
        content = response.get("content", "")
        tool_calls = response.get("tool_calls", [])

        if not content and not tool_calls:
            content = "No response from model"

        # Prepare body_json with tool calls if present
        body_json = {"tool_calls": tool_calls} if tool_calls else None

        # Create assistant message with body_json (handled by message_post override)
        assistant_message = self.message_post(
            body=self._process_llm_body(content) if content else "",
            body_json=body_json,
            llm_role="assistant",
            author_id=False,
        )

        yield {
            "type": "message_create",
            "message": assistant_message.to_store_format(),
        }
        return assistant_message

    def _execute_tool_call(self, tool_call, assistant_message):
        """Execute a single tool call and return the tool message.

        Args:
            tool_call (dict): Tool call data from assistant message
            assistant_message (mail.message): The assistant message that contains the tool calls

        Yields:
            dict: Status updates for streaming

        Returns:
            mail.message: The tool message with execution result
        """
        try:
            # Create tool message using the post_tool_call method
            tool_msg = self.env["mail.message"].post_tool_call(
                tool_call,
                thread_model=self,
            )
            yield {"type": "message_create", "message": tool_msg.to_store_format()}

            # Execute the tool call
            result_msg = yield from tool_msg.execute_tool_call(thread_model=self)
            return result_msg

        except Exception as e:
            _logger.error(f"Error executing tool call: {e}")

            # Create error tool message using the new method
            try:
                error_msg = self.env["mail.message"].create_tool_error_message(
                    tool_call,
                    str(e),
                    thread_model=self,
                )
                yield {
                    "type": "message_create",
                    "message": error_msg.to_store_format(),
                }
                return error_msg
            except Exception as e2:
                _logger.error(f"Failed to create error message: {e2}")
                # Yield error event so frontend knows something went wrong
                yield {
                    "type": "error",
                    "error": f"Tool execution failed: {e!s}",
                }
                # Re-raise the original exception - don't silently return None
                raise e from e2
