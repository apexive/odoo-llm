import logging

from odoo import models

_logger = logging.getLogger(__name__)


class LlmThreadA2a(models.Model):
    """Extend llm.thread to add A2A agent tool definitions to the generation."""

    _inherit = "llm.thread"

    def _prepare_chat_kwargs(self, message_history, use_streaming):
        """Override to include A2A agent delegation tools.

        When A2A agents are assigned to the thread, we dynamically add
        delegation tools that allow the LLM to delegate tasks to those agents.
        """
        chat_kwargs = super()._prepare_chat_kwargs(message_history, use_streaming)

        # If we have A2A agents, pass their tool definitions to the provider
        if self.a2a_agent_ids:
            a2a_tool_definitions = self.get_a2a_tool_definitions()

            if a2a_tool_definitions:
                # Pass A2A tool definitions via kwargs - provider will merge them
                chat_kwargs["a2a_tools"] = a2a_tool_definitions

                _logger.info(
                    "Added %d A2A delegation tools to thread %s",
                    len(a2a_tool_definitions),
                    self.id,
                )

        return chat_kwargs

    def _execute_tool_call(self, tool_call, assistant_message):
        """Override to handle A2A delegation tool calls."""
        # Tool name can be in function.name (OpenAI/Anthropic format) or directly in name
        function_data = tool_call.get("function", {})
        tool_name = function_data.get("name") or tool_call.get("name", "")

        _logger.info("Checking tool call: %s", tool_name)

        # Check if this is an A2A delegation tool
        if tool_name.startswith("delegate_to_"):
            # Extract agent name from tool name
            agent_name_part = tool_name[len("delegate_to_"):]

            _logger.info(
                "A2A delegation detected. Looking for agent: %s in %d agents",
                agent_name_part,
                len(self.a2a_agent_ids),
            )

            # Find the matching A2A agent
            for agent in self.a2a_agent_ids:
                expected_name = agent.name.lower().replace(" ", "_")
                _logger.debug("Comparing '%s' with '%s'", expected_name, agent_name_part)
                if expected_name == agent_name_part:
                    _logger.info("Found matching agent: %s", agent.name)
                    tool_msg = yield from self._execute_a2a_delegation(
                        tool_call, assistant_message, agent
                    )
                    return tool_msg

            # Agent not found - fall through to standard execution which will error
            _logger.warning(
                "A2A agent not found for tool call: %s (looking for: %s)",
                tool_name,
                agent_name_part,
            )

        # Standard tool execution
        tool_msg = yield from super()._execute_tool_call(tool_call, assistant_message)
        return tool_msg

    def _execute_a2a_delegation(self, tool_call, assistant_message, agent):
        """Execute delegation to an A2A agent.

        Args:
            tool_call: The tool call dict from the LLM
            assistant_message: The assistant message containing the tool call
            agent: The llm.a2a.agent record to delegate to

        Yields:
            Status updates for streaming
        """
        import json

        tool_call_id = tool_call.get("id", "unknown")

        # Arguments can be in function.arguments (as JSON string) or directly in arguments
        function_data = tool_call.get("function", {})
        arguments = function_data.get("arguments") or tool_call.get("arguments", {})

        # Parse if it's a JSON string
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {"task": arguments}

        task = arguments.get("task", "")

        _logger.info(
            "Delegating to A2A agent '%s': %s",
            agent.name,
            task[:100] + "..." if len(task) > 100 else task,
        )

        # Create tool message to show delegation in progress
        tool_msg = self.message_post(
            body=f"Delegating to agent: {agent.name}...",
            body_json={
                "tool_call_id": tool_call_id,
                "tool_name": f"delegate_to_{agent.name.lower().replace(' ', '_')}",
                "status": "executing",
                "arguments": arguments,
            },
            llm_role="tool",
            author_id=False,
        )
        yield {"type": "message_create", "message": tool_msg.to_store_format()}

        try:
            # Send message to A2A agent with thread context_id for session continuity
            context_id = f"llm.thread:{self.id}"
            _logger.info("Sending A2A message with context_id: %s", context_id)
            response = agent.send_message(task, context_id=context_id)

            # Parse A2A response to get text content
            result_text = self._parse_a2a_response(response)

            # Update tool message with result
            tool_msg.write(
                {
                    "body": result_text,
                    "body_json": {
                        "tool_call_id": tool_call_id,
                        "tool_name": f"delegate_to_{agent.name.lower().replace(' ', '_')}",
                        "status": "completed",
                        "arguments": arguments,
                        "result": result_text,
                    },
                }
            )

            yield {"type": "message_update", "message": tool_msg.to_store_format()}

            _logger.info("A2A delegation to '%s' completed successfully", agent.name)

        except Exception as e:
            error_msg = f"A2A delegation failed: {str(e)}"
            _logger.error("A2A delegation to '%s' failed: %s", agent.name, e)

            # Update tool message with error
            tool_msg.write(
                {
                    "body": error_msg,
                    "body_json": {
                        "tool_call_id": tool_call_id,
                        "tool_name": f"delegate_to_{agent.name.lower().replace(' ', '_')}",
                        "status": "error",
                        "arguments": arguments,
                        "error": str(e),
                    },
                }
            )

            yield {"type": "message_update", "message": tool_msg.to_store_format()}

        return tool_msg

    def _parse_a2a_response(self, response):
        """Parse A2A response to extract text content.

        Args:
            response: The A2A response dict

        Returns:
            str: Extracted text content
        """
        if isinstance(response, str):
            return response

        if not isinstance(response, dict):
            return str(response)

        result_parts = []

        # Check for message parts
        message = response.get("message", {})
        parts = message.get("parts", [])

        for part in parts:
            if part.get("kind") == "text":
                result_parts.append(part.get("text", ""))

        # Check for artifacts
        artifacts = response.get("artifacts", [])
        for artifact in artifacts:
            artifact_parts = artifact.get("parts", [])
            for part in artifact_parts:
                if part.get("kind") == "text":
                    result_parts.append(part.get("text", ""))

        if result_parts:
            return "\n".join(result_parts)

        # Fallback: return JSON representation
        import json

        return json.dumps(response, indent=2)
