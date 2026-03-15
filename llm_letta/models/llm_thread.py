import logging
from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

# Import render_template from llm_assistant utils
from odoo.addons.llm_assistant.utils import render_template

_logger = logging.getLogger(__name__)

# Constants
LETTA_SERVICE = "letta"
DEFAULT_API_KEY_DURATION = 90.0
LETTA_AGENT_KEY_PREFIX = "Letta Agent - Thread"
DEFAULT_EMBEDDING_MODEL = "openai/text-embedding-3-small"

# Default memory block values
DEFAULT_PERSONA_BLOCK = "I am a helpful AI assistant."
DEFAULT_HUMAN_BLOCK_TEMPLATE = "The human's name is {user_name}."


class LLMThread(models.Model):
    _inherit = "llm.thread"

    external_id = fields.Char(
        string="External ID",
        help="External system identifier (e.g., Letta agent ID)",
        index=True,
    )
    metadata = fields.Json(
        string="Metadata",
        help="Store additional data like API keys for Letta agents",
    )
    is_letta_provider = fields.Boolean(
        string="Is Letta Provider",
        compute="_compute_is_letta_provider",
        store=False,
    )

    @api.depends("provider_id.service")
    def _compute_is_letta_provider(self):
        """Compute if thread uses Letta provider"""
        for thread in self:
            thread.is_letta_provider = (
                thread.provider_id and thread.provider_id.service == LETTA_SERVICE
            )

    def _prepare_chat_kwargs(self, message_history, use_streaming):
        """Override to add thread context for Letta provider."""
        chat_kwargs = super()._prepare_chat_kwargs(message_history, use_streaming)

        # Add thread context for Letta
        if self.provider_id.service == LETTA_SERVICE:
            chat_kwargs["thread_context"] = {"id": self.id}

        return chat_kwargs

    # Metadata helper methods
    def _get_stored_api_key(self, thread):
        """Get API key from thread metadata"""
        if thread.metadata and thread.metadata.get("api_key"):
            return thread.metadata["api_key"]
        return None

    def _store_api_key(self, thread, api_key, api_key_id):
        """Store API key info in thread metadata"""
        thread.metadata = {"api_key": api_key, "api_key_id": api_key_id}

    def _clear_api_key_metadata(self, thread):
        """Clear API key from thread metadata"""
        thread.metadata = {}

    def _get_api_key_name(self, thread_id):
        """Get standardized API key name for thread"""
        return f"{LETTA_AGENT_KEY_PREFIX} {thread_id}"

    @api.model_create_multi
    def create(self, vals_list):
        """Override to create Letta agents when thread is created with Letta provider."""
        threads = super().create(vals_list)

        for thread in threads:
            if thread.provider_id.service == LETTA_SERVICE:
                agent_id = self._create_letta_agent(thread)
                if agent_id:
                    thread.external_id = agent_id

        return threads

    def write(self, vals):
        """Override to handle model/provider changes that require agent recreation."""
        # Handle provider changes first
        self._handle_provider_change(vals)

        result = super().write(vals)

        # Handle Letta-specific updates after write
        if "provider_id" in vals or "model_id" in vals or "assistant_id" in vals:
            self._handle_model_or_provider_change()

        if "tool_ids" in vals:
            self._handle_tool_changes()

        return result

    def _handle_provider_change(self, vals):
        """Handle cleanup when switching away from Letta provider"""
        if "provider_id" not in vals:
            return

        for thread in self:
            if thread.provider_id.service == LETTA_SERVICE:
                new_provider = self.env["llm.provider"].browse(vals["provider_id"])
                if new_provider.service != LETTA_SERVICE:
                    self._cleanup_letta_resources(thread)

    def _handle_model_or_provider_change(self):
        """Handle agent updates when model or provider changes"""
        for thread in self:
            if thread.provider_id.service == LETTA_SERVICE:
                self._update_or_create_agent(thread)

    def _handle_tool_changes(self):
        """Handle tool synchronization for Letta agents"""
        for thread in self:
            if thread.provider_id.service == LETTA_SERVICE and thread.external_id:
                thread.provider_id.letta_sync_agent_tools(
                    thread.external_id, thread.tool_ids
                )

    def _update_or_create_agent(self, thread):
        """Update existing agent or create new one"""
        if thread.external_id:
            # Agent exists - update it
            client = thread.provider_id.letta_get_client()

            # Build system instruction for updates
            system_instruction = None
            if thread.assistant_id and thread.assistant_id.prompt_id:
                context = thread.get_context()
                system_instruction = render_template(
                    template=thread.assistant_id.prompt_id.template, context=context
                )

            modify_params = {
                "model": thread.model_id.name,
            }
            if system_instruction:
                modify_params["system"] = system_instruction

            client.agents.update(thread.external_id, **modify_params)
        else:
            # No agent exists - create one
            agent_id = self._create_letta_agent(thread)
            thread.external_id = agent_id

    def unlink(self):
        """Clean up Letta resources when thread is deleted"""
        for thread in self:
            if thread.provider_id.service == LETTA_SERVICE:
                self._cleanup_letta_resources(thread)
        return super().unlink()

    def _cleanup_letta_resources(self, thread):
        """Clean up API keys and Letta agent when thread is deleted or provider changed"""
        # Delete API key if exists
        if thread.metadata and thread.metadata.get("api_key_id"):
            api_key_record = (
                self.env["res.users.apikeys"]
                .sudo()
                .browse(thread.metadata["api_key_id"])
            )
            if api_key_record.exists():
                api_key_record.unlink()

        # Delete Letta agent if exists (allow this to fail silently as resource might be already gone)
        if thread.external_id:
            try:
                client = thread.provider_id.letta_get_client()
                client.agents.delete(thread.external_id)
                _logger.info(f"Deleted Letta agent {thread.external_id}")
            except Exception:
                # Agent might already be deleted or server unreachable - this is OK during cleanup
                _logger.debug(
                    f"Could not delete Letta agent {thread.external_id} (may already be gone)"
                )

        # Clear metadata and external_id
        self._clear_api_key_metadata(thread)
        thread.external_id = False

    def _create_letta_agent(self, thread):
        """Create a Letta agent for the given thread.

        Args:
            thread: llm.thread record

        Returns:
            str: Agent ID if successful, None otherwise
        """
        if not thread.model_id:
            return None

        # Get Letta client from provider
        client = thread.provider_id.letta_get_client()
        # Build agent configuration
        agent_config = self._build_agent_config(thread)
        # Create agent
        agent = client.agents.create(**agent_config)
        agent_id = agent.id

        # Sync tools after creation if thread has any
        if thread.tool_ids:
            thread.provider_id.letta_sync_agent_tools(agent_id, thread.tool_ids)

        return agent_id

    def _build_agent_config(self, thread):
        """Build agent configuration from thread context.

        Args:
            thread: llm.thread record

        Returns:
            dict: Agent configuration for Letta API
        """
        user_name = thread.user_id.name or "User"

        # Build memory blocks from thread context
        memory_blocks = [
            {"label": "persona", "value": DEFAULT_PERSONA_BLOCK},
            {
                "label": "human",
                "value": DEFAULT_HUMAN_BLOCK_TEMPLATE.format(user_name=user_name),
            },
        ]

        # Use the actual selected model (should already include provider prefix)
        model_name = thread.model_id.name

        # Get or create API key for MCP authentication
        api_key = self._ensure_api_key_for_agent(thread)

        # Add system instruction if assistant is available
        system_instruction = None
        if thread.assistant_id and thread.assistant_id.prompt_id:
            context = thread.get_context()
            system_instruction = render_template(
                template=thread.assistant_id.prompt_id.template, context=context
            )

        embedding = thread.provider_id.letta_get_embedding_model()
        if not embedding:
            raise UserError(
                _(
                    "No embedding models are configured for the Letta provider '%s'.\n\n"
                    "To fix this:\n"
                    "1. Go to LLM → Configuration → Providers\n"
                    "2. Select the '%s' provider\n"
                    "3. Click 'Fetch Models' to import available models"
                )
                % (thread.provider_id.name, thread.provider_id.name)
            )

        # Build full configuration
        agent_config = {
            "name": f"thread_{thread.id}",
            "model": model_name,
            "embedding": embedding,
            "memory_blocks": memory_blocks,
            "tools": thread.provider_id.letta_format_tools([]),  # Basic tools for now
        }

        # Add system instruction if available
        if system_instruction:
            agent_config["system"] = system_instruction

        agent_config["tool_exec_environment_variables"] = {
            "ODOO_API_KEY": api_key,
        }

        return agent_config

    def _ensure_api_key_for_agent(self, thread):
        """Get or create API key for Letta agent MCP authentication"""
        # Check if we already have an API key
        existing_key = self._get_stored_api_key(thread)
        if existing_key:
            return existing_key

        # Generate new API key with scope 'rpc'
        max_duration = max(
            (
                group.api_key_duration
                for group in thread.user_id.groups_id
                if group.api_key_duration
            ),
            default=DEFAULT_API_KEY_DURATION,
        )

        expiration_date = datetime.now() + timedelta(days=max_duration)
        api_key_name = self._get_api_key_name(thread.id)

        # Generate API key programmatically
        api_key = (
            self.env["res.users.apikeys"]
            .sudo()
            .with_user(thread.user_id)
            ._generate(scope="rpc", name=api_key_name, expiration_date=expiration_date)
        )

        # Find the created API key record to get its ID
        api_key_record = (
            self.env["res.users.apikeys"]
            .sudo()
            .search(
                [
                    ("user_id", "=", thread.user_id.id),
                    ("name", "=", api_key_name),
                ],
                limit=1,
                order="create_date desc",
            )
        )

        # Store API key info in metadata
        self._store_api_key(
            thread, api_key, api_key_record.id if api_key_record else None
        )

        return api_key

    def get_letta_agent_id(self):
        """Get the Letta agent ID for this thread.

        Returns:
            str: Agent ID if available, None otherwise
        """
        self.ensure_one()

        if self.provider_id.service == "letta":
            return self.external_id
        else:
            return None

    def ensure_letta_agent(self):
        """Ensure this thread has a valid Letta agent.

        Returns:
            str: Agent ID

        Raises:
            UserError: If agent cannot be created or verified
        """
        self.ensure_one()

        if self.provider_id.service != "letta":
            raise UserError(
                _("This action is only available for Letta-powered conversations.")
            )

        agent_id = self.external_id

        # Verify agent exists in Letta
        if agent_id:
            client = self.provider_id.letta_get_client()
            client.agents.retrieve(agent_id)
            return agent_id

        # Create new agent if needed
        if not agent_id:
            agent_id = self._create_letta_agent(self)
            if agent_id:
                self.external_id = agent_id
            else:
                raise UserError(
                    _(
                        "Could not initialize the AI assistant for this conversation. "
                        "Please check the provider configuration or contact your administrator."
                    )
                )

        return agent_id

    def sync_letta_tools(self):
        """Manual tool synchronization for Letta agent"""
        self.ensure_one()

        if self.provider_id.service != "letta":
            raise UserError(
                _("This action is only available for Letta-powered conversations.")
            )

        if not self.external_id:
            raise UserError(
                _(
                    "The AI assistant for this conversation is not available. "
                    "Please refresh or start a new conversation."
                )
            )

        self.provider_id.letta_sync_agent_tools(self.external_id, self.tool_ids)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "message": f"Tools synchronized successfully for agent {self.external_id}",
                "type": "success",
            },
        }

    def _process_llm_body(self, body):
        """Override to handle Letta's specific escape sequence formatting."""
        if not body:
            return body

        # Only apply Letta-specific cleaning if using Letta provider
        # This preserves emojis and other unicode characters
        if self.provider_id and self.provider_id.service == "letta":
            # Handle Letta's split escape sequences
            body = body.replace("\\n", "\n").replace("\\t", "\t").replace("\\r", "\r")

        # Call parent's implementation for standard markdown processing
        return super()._process_llm_body(body)
