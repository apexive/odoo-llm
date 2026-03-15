# Note: Using letta-client SDK (Stainless-generated)
from letta_client import Letta
from letta_client.types import CreateStreamableHTTPMcpServerParam, MessageCreateParam

from odoo import _, api, models
from odoo.exceptions import UserError


class LLMProvider(models.Model):
    _inherit = "llm.provider"

    @api.model
    def _get_available_services(self):
        services = super()._get_available_services()
        return services + [("letta", "Letta")]

    def letta_get_client(self):
        """Get Letta client instance"""
        if not self.api_base:
            raise UserError(
                _(
                    "Please configure the API base URL in the provider settings to connect to Letta."
                )
            )

        # Simple unified initialization for both local and cloud
        return Letta(
            base_url=self.api_base,
            api_key=self.api_key,
        )

    def letta_normalize_prepend_messages(self, prepend_messages):
        """Normalize prepend_messages for Letta.

        Letta agents maintain their own conversation history,
        so we just pass through the messages unchanged.
        """
        return prepend_messages or []

    def letta_models(self, model_id=None):
        """List available models from Letta"""
        client = self.letta_get_client()
        models_response = client.models.list()
        embedding_models_response = client.models.embeddings.list()

        models = []

        # Process chat/completion models
        for model in models_response:
            model_data = self._letta_parse_llm_model(model)
            if model_id and model_data["name"] != model_id:
                continue
            models.append(model_data)

        # Process embedding models
        for model in embedding_models_response:
            model_data = self._letta_parse_embedding_model(model)
            if model_id and model_data["name"] != model_id:
                continue
            models.append(model_data)

        return models

    def _letta_parse_llm_model(self, model):
        """Parse a chat/completion model from Letta API"""
        # Use handle as the name since that's what Letta agent config expects
        model_handle = getattr(model, "handle", None)
        if not model_handle:
            # Fallback: construct handle if not provided
            provider = getattr(model, "model_endpoint_type", "unknown")
            model_name = getattr(model, "model", "unknown")
            model_handle = f"{provider}/{model_name}"

        return {
            "name": model_handle,
            "details": {
                "provider": getattr(model, "provider_name", "letta"),
                "context_window": getattr(model, "context_window", None),
                "model_endpoint_type": getattr(model, "model_endpoint_type", None),
                "temperature": getattr(model, "temperature", None),
                "max_tokens": getattr(model, "max_tokens", None),
                "raw_model_name": getattr(model, "model", None),
                "capabilities": ["chat"],  # Used by wizard to determine model_use
            },
        }

    def _letta_parse_embedding_model(self, model):
        """Parse an embedding model from Letta API"""
        # Use handle as the name
        model_handle = getattr(model, "handle", None)
        if not model_handle:
            # Fallback: construct handle if not provided
            provider = getattr(model, "embedding_endpoint_type", "unknown")
            model_name = getattr(model, "embedding_model", "unknown")
            model_handle = f"{provider}/{model_name}"

        return {
            "name": model_handle,
            "details": {
                "provider": getattr(model, "embedding_endpoint_type", "letta"),
                "embedding_dim": getattr(model, "embedding_dim", None),
                "embedding_chunk_size": getattr(model, "embedding_chunk_size", None),
                "batch_size": getattr(model, "batch_size", None),
                "embedding_endpoint": getattr(model, "embedding_endpoint", None),
                "raw_model_name": getattr(model, "embedding_model", None),
                "capabilities": ["embedding"],  # Used by wizard to determine model_use
            },
        }

    def letta_get_embedding_model(self):
        """Get the best available embedding model for this Letta provider.

        Priority:
        1. Default embedding model (default=True)
        2. First available embedding model

        Returns:
            str: The embedding model name/handle
        """
        # Get all embedding models for this provider
        embedding_models = self.env["llm.model"].search(
            [
                ("provider_id", "=", self.id),
                ("model_use", "=", "embedding"),
                ("active", "=", True),
            ]
        )

        if not embedding_models:
            return None

        # Try to find default embedding model
        default_models = embedding_models.filtered("default")
        if default_models:
            # If multiple defaults, just use the first one silently
            return default_models[0].name

        # Use first available embedding model
        return embedding_models[0].name

    def letta_chat(self, messages, model=None, stream=False, **kwargs):  # pylint: disable=unused-argument
        """Chat completion using Letta agents.

        Args:
            messages: List of messages (only latest user message is used)
            model: Model to use (ignored - agent already has model)
            stream: Whether to stream response
            **kwargs: Additional parameters, including thread context

        Returns:
            Generator of response chunks if streaming, else complete response
        """
        client = self.letta_get_client()

        # Get thread from context
        thread_context = kwargs.get("thread_context", {})
        thread_id = thread_context.get("id")

        if not thread_id:
            raise UserError(
                _(
                    "Unable to start chat. Please try again from an active conversation thread."
                )
            )

        # Get thread record and ensure it has a Letta agent
        thread_record = self.env["llm.thread"].browse(thread_id)
        if not thread_record.exists():
            raise UserError(
                _("The conversation could not be found. It may have been deleted.")
            )

        agent_id = thread_record.ensure_letta_agent()

        # Extract latest user message - Letta agents maintain their own history
        latest_message = messages[-1] if messages else None
        if not latest_message:
            raise UserError(_("Please enter a message before sending."))

        # Use the standard dispatch to format the message
        formatted_message = self._dispatch("format_message", record=latest_message)
        if not formatted_message or not formatted_message.get("content"):
            raise UserError(
                _(
                    "Your message could not be processed. Please try rephrasing and sending again."
                )
            )

        user_content = formatted_message["content"]

        if stream:
            return self._letta_stream_agent_response(client, agent_id, user_content)
        else:
            return self._letta_get_agent_response(client, agent_id, user_content)

    def letta_format_tools(self, tools):
        """Format tools for Letta (not used - tools are managed via MCP/API)."""
        return []

    def letta_ensure_mcp_server(self):
        """Ensure Odoo MCP server is registered with Letta."""
        client = self.letta_get_client()

        # Get MCP server config
        mcp_config_model = self.env["llm.mcp.server.config"]
        mcp_config = mcp_config_model.get_active_config()
        server_name = mcp_config.name

        # Check if server already exists
        servers = client.mcp_servers.list()

        # Check if our server is already registered
        server_exists = False
        for server in servers:
            # Server list returns dict with server_name as key
            if isinstance(server, dict):
                if server_name in server:
                    server_exists = True
                    break
            elif hasattr(server, "server_name") and server.server_name == server_name:
                server_exists = True
                break

        if server_exists:
            return True

        # Get MCP server URL from configuration
        server_url = mcp_config.get_mcp_server_url()

        # Create the proper MCP server config using Letta client types
        config_param = CreateStreamableHTTPMcpServerParam(
            server_url=server_url,
            mcp_server_type="streamable_http",
            custom_headers={
                # Letta will replace this template with API key from environment variables
                "Authorization": "Bearer {{ ODOO_API_KEY | system-api-key }}",
            },
        )

        # Register the MCP server using the correct API
        client.mcp_servers.create(config=config_param, server_name=server_name)
        return True

    def letta_attach_tool(self, agent_id, tool_name):
        """Attach a specific tool to a Letta agent."""
        client = self.letta_get_client()

        # First ensure MCP server is registered
        self.letta_ensure_mcp_server()

        # Get MCP server config for server name
        mcp_config_model = self.env["llm.mcp.server.config"]
        mcp_config = mcp_config_model.get_active_config()
        server_name = mcp_config.name

        # Get MCP server ID from server name
        servers = client.mcp_servers.list()
        mcp_server_id = None
        for server in servers:
            if hasattr(server, "server_name") and server.server_name == server_name:
                mcp_server_id = server.id
                break

        if not mcp_server_id:
            raise UserError(
                _("MCP server '%s' not found. Please ensure it is properly configured.")
                % server_name
            )

        # In the new SDK, MCP tools are auto-synced to the global tools registry
        # We don't need to check the MCP server endpoint as it's just a view
        # Instead, we look directly in the global tools list
        all_tools = client.tools.list()
        tool_id = None
        for tool in all_tools:
            if hasattr(tool, "name") and tool.name == tool_name:
                tool_id = tool.id
                break

        if not tool_id:
            raise UserError(
                _(
                    "The tool '%s' could not be found in the tools registry. Please try refreshing the MCP server."
                )
                % tool_name
            )

        # Attach tool to agent (tool_id is positional, agent_id is keyword-only)
        attach_response = client.agents.tools.attach(tool_id, agent_id=agent_id)
        return attach_response

    def letta_detach_tool(self, agent_id, tool_name):
        """Detach a tool from a Letta agent."""
        client = self.letta_get_client()

        # Get agent's current tools
        agent_tools = client.agents.tools.list(agent_id)

        # Find the tool to detach - agent_tools is List[Tool]
        tool_to_detach = None
        for tool in agent_tools:
            if tool.name == tool_name:
                tool_to_detach = tool
                break

        if not tool_to_detach:
            return False

        # Get tool ID from the Tool object
        if not tool_to_detach.id:
            raise UserError(
                _(
                    "Could not deactivate the tool '%s'. Please try again or contact your administrator."
                )
                % tool_name
            )

        # Detach tool from agent (tool_id is positional, agent_id is keyword-only)
        detach_response = client.agents.tools.detach(
            tool_to_detach.id, agent_id=agent_id
        )
        return detach_response

    def letta_sync_agent_tools(self, agent_id, tool_records):
        """Synchronize agent tools with thread tool_ids."""

        if not tool_records:
            # Remove all tools from agent if no tools specified
            client = self.letta_get_client()
            agent_tools = client.agents.tools.list(agent_id)
            mcp_tools = []
            for tool in agent_tools:
                if tool.tool_type == "external_mcp":
                    mcp_tools.append(tool)

            for tool in mcp_tools:
                self.letta_detach_tool(agent_id, tool.name)
            return

        # Get all tools from the thread (regardless of implementation type)
        thread_tools = tool_records.filtered(lambda t: t.active)

        if not thread_tools:
            return

        # Get current agent tools
        client = self.letta_get_client()
        agent_tools = client.agents.tools.list(agent_id)

        # Extract current MCP tool names from Tool objects
        current_tool_names = set()
        for tool in agent_tools:
            if tool.tool_type == "external_mcp":
                current_tool_names.add(tool.name)

        # Get desired tool names from the thread's tool_ids
        desired_tool_names = set(thread_tools.mapped("name"))

        # Attach new tools
        tools_to_attach = desired_tool_names - current_tool_names
        for tool_name in tools_to_attach:
            self.letta_attach_tool(agent_id, tool_name)

        # Detach removed tools
        tools_to_detach = current_tool_names - desired_tool_names
        for tool_name in tools_to_detach:
            self.letta_detach_tool(agent_id, tool_name)

    def letta_format_messages(self, messages, system_prompt=None):
        """Format messages for Letta (simplified - agent maintains history).

        Note: Letta agents maintain their own conversation history,
        so we only need to return the latest user message.
        """
        if not messages:
            return []

        # Return only the latest message - Letta handles conversation state
        latest_message = messages[-1]
        formatted_message = self._dispatch("format_message", record=latest_message)
        return [formatted_message] if formatted_message else []

    def _letta_stream_agent_response(self, client, agent_id, user_content):
        """Stream response from Letta agent."""

        stream = client.agents.messages.create(
            agent_id=agent_id,
            messages=[MessageCreateParam(role="user", content=user_content)],
            streaming=True,
            stream_tokens=True,  # Enable token-level streaming for real-time updates
        )

        response_content = ""

        for chunk in stream:
            # Check if chunk has message_type attribute (Letta's streaming format)
            if hasattr(chunk, "message_type"):
                message_type = getattr(chunk, "message_type", None)
                content = getattr(chunk, "content", None)

                # Extract text content from content attribute (could be string or list)
                content_text = ""
                if isinstance(content, str):
                    content_text = content
                elif isinstance(content, list) and len(content) > 0:
                    # Content is a list of content parts, extract text from each
                    for part in content:
                        if isinstance(part, dict) and "text" in part:
                            content_text += part["text"]
                        elif hasattr(part, "text"):
                            content_text += part.text

                # Handle assistant message chunks
                if message_type == "assistant_message" and content_text:
                    response_content += content_text
                    yield {"content": content_text}

        # Yield final response
        yield {"content": "", "finish_reason": "stop"}

    def _letta_get_agent_response(self, client, agent_id, user_content):
        """Get non-streaming response from Letta agent."""

        # For non-streaming, we'll collect the full response
        response_content = ""

        stream = client.agents.messages.create(
            agent_id=agent_id,
            messages=[MessageCreateParam(role="user", content=user_content)],
            streaming=False,
        )

        for chunk in stream:
            # Check if chunk has message_type attribute (Letta's streaming format)
            if hasattr(chunk, "message_type"):
                message_type = getattr(chunk, "message_type", None)

                # Handle assistant message chunks
                if message_type == "assistant_message" and hasattr(chunk, "content"):
                    if chunk.content:
                        response_content += chunk.content

        return {
            "content": response_content or "I couldn't generate a response.",
            "finish_reason": "stop",
        }
