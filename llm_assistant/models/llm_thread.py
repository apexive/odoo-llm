import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class LLMThread(models.Model):
    _inherit = "llm.thread"

    assistant_id = fields.Many2one(
        "llm.assistant",
        string="Assistant",
        ondelete="restrict",
        help="The assistant used for this thread",
    )

    @api.onchange("assistant_id")
    def _onchange_assistant_id(self):
        """Update provider, model and tools when assistant changes"""
        if self.assistant_id:
            self.provider_id = self.assistant_id.provider_id
            self.model_id = self.assistant_id.model_id
            self.tool_ids = self.assistant_id.tool_ids

    def set_assistant(self, assistant_id):
        """Set the assistant for this thread and update related fields

        Args:
            assistant_id (int): The ID of the assistant to set

        Returns:
            bool: True if successful, False otherwise
        """
        self.ensure_one()

        # If assistant_id is False or 0, just clear the assistant
        if not assistant_id:
            return self.write({"assistant_id": False})

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
        if assistant.prompt_id and not self.prompt_id:
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

    # override to include assistant's messages
    def _get_prepend_messages(self):
        """Hook: return a list of formatted messages to prepend to the conversation.
        Override in other modules if needed.

        Returns:
            list: List of message dictionaries in the format:
                [{"role": "system", "content": "..."},
                 {"role": "user", "content": "..."},
                 ...]
        """
        self.ensure_one()
        # Get base messages from parent class
        messages = super()._get_prepend_messages()

        # Get messages from assistant if available
        if self.assistant_id:
            # Use the new get_messages method which returns a list of messages
            assistant_messages = self.assistant_id.get_messages(thread=self)

            if assistant_messages:
                # Use the helper method from llm_prompt to merge the messages
                messages = self.merge_message_lists(assistant_messages, messages)
                _logger.info(
                    "Added %d messages from assistant", len(assistant_messages)
                )
            else:
                # Fallback to the old method if get_messages returns empty
                # This ensures backward compatibility
                assistant_system_prompt = self.assistant_id.get_formatted_system_prompt(
                    thread=self
                )
                if assistant_system_prompt:
                    # Create a system message with the assistant's prompt
                    assistant_message = {
                        "role": "system",
                        "content": assistant_system_prompt,
                    }

                    # Add it to existing messages or create a new list
                    if messages:
                        # Check if there's already a system message
                        has_system_message = False
                        for msg in messages:
                            if msg.get("role") == "system":
                                # Append to existing system message
                                msg["content"] = (
                                    f"{assistant_system_prompt}\n\n{msg['content']}"
                                )
                                has_system_message = True
                                break

                        # If no system message found, add the new one at the beginning
                        if not has_system_message:
                            messages.insert(0, assistant_message)
                    else:
                        # No existing messages, create a new list with just the system message
                        messages = [assistant_message]

                    _logger.info(
                        "Added system message from assistant: %s",
                        assistant_system_prompt,
                    )

        return messages

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
