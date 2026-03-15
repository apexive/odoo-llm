import logging

from odoo import models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class LLMAssistantActionMixin(models.AbstractModel):
    """
    Mixin to add AI assistant action functionality to any model.
    Provides generic methods to open LLM chat with specific assistants.

    Usage:
        class MyModel(models.Model):
            _inherit = ['my.model', 'llm.assistant.action.mixin']

            def action_my_ai_button(self):
                return self.action_open_llm_assistant('my_assistant_code')
    """

    _name = "llm.assistant.action.mixin"
    _description = "LLM Assistant Action Mixin"

    def action_open_llm_assistant(
        self, assistant_code=None, force_new_thread=False, **kwargs
    ):
        """
        Generic method to open AI assistant for current record.
        Creates/finds thread, sets assistant, and prepares for frontend to open AI chat.

        Args:
            assistant_code: Code of the assistant to use (e.g., 'invoice_analyzer').
                           If not provided, tries to get from context.
            force_new_thread: If True, always create new thread (ignore existing).
            **kwargs: Reserved for future extensibility.

        Returns:
            dict: Client action to open AI chat in chatter

        Raises:
            UserError: If no provider/model found
        """
        self.ensure_one()

        # Get assistant code from parameter or context
        if not assistant_code:
            assistant_code = self.env.context.get("assistant_code")

        if not assistant_code:
            raise UserError(
                "No assistant code provided. Please specify assistant_code parameter or context."
            )

        _logger.info(
            "=== Opening AI assistant '%s' for %s ID: %s (force_new=%s) ===",
            assistant_code,
            self._name,
            self.id,
            force_new_thread,
        )

        # Find existing thread or create new one
        thread = self._find_or_create_llm_thread(force_new=force_new_thread)

        # Find and set assistant
        self._set_assistant_on_thread(thread, assistant_code)

        _logger.info(
            "=== AI assistant ready. Thread ID: %s, Assistant: %s ===",
            thread.id,
            thread.assistant_id.name if thread.assistant_id else "None",
        )

        # Return client action to open AI chat in chatter
        # This is more reliable than bus notifications which can fail on cloud
        # deployments with WebSocket issues
        return {
            "type": "ir.actions.client",
            "tag": "llm_open_chatter",
            "params": {
                "thread_id": thread.id,
                "model": self._name,
                "res_id": self.id,
            },
        }

    def _find_or_create_llm_thread(self, force_new=False):
        """
        Find existing thread for this record or create a new one.

        Args:
            force_new: If True, always create new thread (ignore existing)

        Returns:
            llm.thread: The thread record
        """
        if not force_new:
            _logger.info("Step 1: Looking for existing thread...")
            thread = self.env["llm.thread"].search(
                [("model", "=", self._name), ("res_id", "=", self.id)], limit=1
            )

            if thread:
                _logger.info("Found existing thread ID: %s", thread.id)
                return thread

        _logger.info("Creating new thread...")

        # Find default chat model or fallback to first available
        _logger.info("Looking for default chat model...")
        default_model = self.env["llm.model"].search(
            [
                ("model_use", "in", ["chat", "multimodal"]),
                ("default", "=", True),
                ("active", "=", True),
            ],
            limit=1,
        )

        if default_model:
            _logger.info(
                "Found default model: %s (Provider: %s)",
                default_model.name,
                default_model.provider_id.name,
            )
        else:
            _logger.info("No default model found, looking for first available...")

            # Fallback: Get first provider and its first chat model
            _logger.info("Looking for first available provider...")
            provider = self.env["llm.provider"].search([("active", "=", True)], limit=1)
            if not provider:
                _logger.error("No active LLM provider found!")
                raise UserError(
                    "No active LLM provider found. Please configure a provider first."
                )

            _logger.info("Found provider: %s", provider.name)
            _logger.info("Looking for first chat model for this provider...")
            default_model = self.env["llm.model"].search(
                [
                    ("provider_id", "=", provider.id),
                    ("model_use", "in", ["chat", "multimodal"]),
                    ("active", "=", True),
                ],
                limit=1,
            )

        if not default_model:
            _logger.error("No active chat model found!")
            raise UserError(
                "No active chat model found. Please configure a model first."
            )

        _logger.info(
            "Creating new thread with Provider: %s, Model: %s",
            default_model.provider_id.name,
            default_model.name,
        )

        # Create new thread - name will be auto-generated by backend
        thread = self.env["llm.thread"].create(
            {
                "model": self._name,
                "res_id": self.id,
                "provider_id": default_model.provider_id.id,
                "model_id": default_model.id,
            }
        )
        _logger.info("Thread created successfully with ID: %s", thread.id)

        return thread

    def _set_assistant_on_thread(self, thread, assistant_code):
        """
        Find assistant by code and set it on the thread.

        Args:
            thread: llm.thread record
            assistant_code: Code of the assistant to find
        """
        _logger.info("Step 2: Looking for assistant with code '%s'...", assistant_code)
        assistant = self.env["llm.assistant"].search(
            [("code", "=", assistant_code)], limit=1
        )

        if assistant:
            _logger.info("Found assistant: %s (ID: %s)", assistant.name, assistant.id)
            if not thread.assistant_id:
                _logger.info(
                    "Setting assistant on thread (with tools, provider, model)..."
                )
                thread.set_assistant(assistant.id)
                _logger.info(
                    "Assistant set successfully. Tools: %s",
                    thread.tool_ids.mapped("name"),
                )
            else:
                _logger.info(
                    "Thread already has assistant: %s", thread.assistant_id.name
                )
        else:
            _logger.warning("Assistant with code '%s' not found!", assistant_code)
