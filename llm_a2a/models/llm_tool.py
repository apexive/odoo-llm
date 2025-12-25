import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class LlmTool(models.Model):
    _inherit = "llm.tool"

    @api.model
    def _get_available_implementations(self):
        """Add a2a_delegate implementation type."""
        implementations = super()._get_available_implementations()
        implementations.append(("a2a_delegate", "A2A Agent Delegation"))
        return implementations

    # A2A-specific fields
    a2a_agent_id = fields.Many2one(
        "llm.a2a.agent",
        string="A2A Agent",
        help="The A2A agent to delegate to when this tool is called",
    )

    def a2a_delegate_execute(self, task: str, **kwargs):
        """Execute delegation to an A2A agent.

        Args:
            task: The task description to send to the agent

        Returns:
            str: Response from the A2A agent
        """
        self.ensure_one()

        if not self.a2a_agent_id:
            raise UserError(_("No A2A agent configured for this tool"))

        # Use sudo() to bypass record rules - any user with access to the tool
        # should be able to execute it via the A2A agent
        agent = self.a2a_agent_id.sudo()

        # Get context_id from message context (thread res_id) for conversation continuity
        context_id = kwargs.get("context_id")
        if not context_id:
            # Try to get from message context - use thread id as context
            message = self.env.context.get("message")
            _logger.info("A2A context: message=%s, res_id=%s, model=%s",
                        message, getattr(message, 'res_id', None) if message else None,
                        getattr(message, 'model', None) if message else None)
            if message and message.res_id:
                # Use model:res_id as unique context identifier
                context_id = f"{message.model}:{message.res_id}"
                _logger.info("Using thread context_id for A2A: %s", context_id)
            else:
                _logger.warning("No message context or res_id available for A2A context_id")

        _logger.info(
            "Delegating task to A2A agent '%s': %s",
            agent.name,
            task[:100] + "..." if len(task) > 100 else task,
        )

        try:
            # Send message to A2A agent
            response = agent.send_message(task, context_id=context_id)

            # Parse A2A response
            if isinstance(response, dict):
                # Extract text from response parts
                result_parts = []

                # Handle task result
                if "result" in response:
                    result = response["result"]
                    if isinstance(result, dict):
                        # Check for message parts
                        message = result.get("message", {})
                        parts = message.get("parts", [])
                        for part in parts:
                            if part.get("kind") == "text":
                                result_parts.append(part.get("text", ""))
                            elif part.get("kind") == "data":
                                result_parts.append(json.dumps(part.get("data", {})))

                        # Check for artifacts
                        artifacts = result.get("artifacts", [])
                        for artifact in artifacts:
                            parts = artifact.get("parts", [])
                            for part in parts:
                                if part.get("kind") == "text":
                                    result_parts.append(part.get("text", ""))

                if result_parts:
                    return "\n".join(result_parts)
                else:
                    return json.dumps(response, indent=2)

            return str(response)

        except Exception as e:
            _logger.error("A2A delegation failed for agent '%s': %s", agent.name, e)
            raise UserError(_("A2A delegation failed: %s") % str(e))

    def get_input_schema(self):
        """Override to provide A2A delegation schema."""
        self.ensure_one()

        if self.implementation == "a2a_delegate":
            # Use agent's tool definition schema if available
            if self.a2a_agent_id:
                tool_def = self.a2a_agent_id.get_tool_definition()
                return tool_def.get("inputSchema", {
                    "type": "object",
                    "properties": {
                        "task": {
                            "type": "string",
                            "description": "The task or question to delegate to this agent",
                        },
                    },
                    "required": ["task"],
                })
            else:
                return {
                    "type": "object",
                    "properties": {
                        "task": {
                            "type": "string",
                            "description": "The task or question to delegate to the A2A agent",
                        },
                    },
                    "required": ["task"],
                }

        return super().get_input_schema()
