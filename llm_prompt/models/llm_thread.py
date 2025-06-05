import json
import logging

from odoo import fields, models, tools

_logger = logging.getLogger(__name__)


class LLMThreadPrompt(models.Model):
    _inherit = "llm.thread"

    prompt_id = fields.Many2one(
        "llm.prompt",
        string="Prompt for workflow",
        ondelete="restrict",
        tracking=True,
        help="Prompt to use for workflow",
    )

    def merge_message_lists(self, source_messages, target_messages):
        """Merge two lists of messages, handling system messages appropriately

        This helper method merges two lists of messages, ensuring that system messages
        are properly combined without duplication.

        Args:
            source_messages (list): The source list of messages to merge from
            target_messages (list): The target list of messages to merge into

        Returns:
            list: The merged list of messages
        """
        if not source_messages:
            return target_messages

        if not target_messages:
            return (
                source_messages.copy()
            )  # Return a copy to avoid modifying the original

        # Make a copy of source messages to avoid modifying the original
        source_messages_copy = source_messages.copy()

        # Check for system messages to avoid duplicates
        system_messages_in_source = [
            msg for msg in source_messages_copy if msg.get("role") == "system"
        ]
        system_messages_in_target = [
            msg for msg in target_messages if msg.get("role") == "system"
        ]

        if system_messages_in_source and system_messages_in_target:
            # Both have system messages, merge them
            for source_msg in system_messages_in_source:
                for target_msg in system_messages_in_target:
                    target_msg[
                        "content"
                    ] = f"{source_msg['content']}\n\n{target_msg['content']}"
                # Remove the source system message as we've merged it
                source_messages_copy.remove(source_msg)

        # Now add any remaining source messages at the beginning
        return source_messages_copy + target_messages

    # override to include prompt messages
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

        # Get messages from the prompt if available
        if self.prompt_id:
            # Create a context with the thread_id
            context = dict(self.env.context, thread_id=self.id)
            # Use the prompt to get messages with the new context
            arguments = self._get_prompt_default_arguments()
            prompt_messages = self.with_context(context).prompt_id.get_messages(
                arguments
            )
            if prompt_messages:
                messages = self.merge_message_lists(prompt_messages, messages)
                _logger.info("Added %d messages from prompt", len(prompt_messages))

        return messages

    def _get_prompt_default_arguments(self):
        """Return the arguments of the last message.

        Returns:
            dict: Dictionary of arguments in the last message.
        """
        last_message = tools.html2plaintext(self.message_ids[0].body)
        return json.loads(last_message)
