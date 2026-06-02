import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class LlmThread(models.Model):
    _inherit = "llm.thread"

    a2a_agent_ids = fields.Many2many(
        "llm.a2a.agent",
        string="A2A Agents",
        help="External A2A agents that can be delegated to in this thread",
        domain="[('state', '=', 'connected')]",
    )

    def _thread_to_store(self, store, **kwargs):
        """Extend to include A2A agents in store data."""
        super()._thread_to_store(store, **kwargs)

        for thread in self:
            if thread.a2a_agent_ids:
                # Add A2A agents data to the thread
                store.add(
                    "mail.thread",
                    {
                        "id": thread.id,
                        "model": "llm.thread",
                        "a2a_agent_ids": [
                            {
                                "id": agent.id,
                                "name": agent.name,
                                "model": "llm.a2a.agent",
                                "description": agent.agent_description or "",
                                "skills": agent.agent_skills or "",
                                "state": agent.state,
                            }
                            for agent in thread.a2a_agent_ids
                        ],
                    },
                )

    def get_a2a_tool_definitions(self):
        """Get tool definitions for all A2A agents assigned to this thread.

        These tools allow the LLM to delegate tasks to external agents.
        """
        self.ensure_one()
        tools = []

        for agent in self.a2a_agent_ids:
            if agent.state == "connected":
                tools.append(agent.get_tool_definition())

        return tools

    def get_prepend_messages(self):
        """Override to add A2A agent capability instructions to the system prompt.

        This method only adds A2A-specific capabilities.
        Other capabilities (RAG, Tools) are handled by their respective modules.

        Note: llm_knowledge module handles RAG context separately.
        """
        messages = super().get_prepend_messages()

        # Only add A2A agent descriptions if configured
        if not self.a2a_agent_ids:
            return messages

        a2a_descriptions = []
        for agent in self.a2a_agent_ids:
            if agent.state == "connected":
                tool_name = f"delegate_to_{agent.name.lower().replace(' ', '_')}"
                desc = agent.agent_description or f"Agent: {agent.name}"
                skills = agent.agent_skills or ""

                agent_desc = f"- **{agent.name}** (tool: `{tool_name}`)\n"
                agent_desc += f"  Description: {desc}\n"
                if skills:
                    agent_desc += f"  Skills: {skills}\n"

                a2a_descriptions.append(agent_desc)

        if a2a_descriptions:
            a2a_system_prompt = {
                "role": "system",
                "content": (
                    "# External Agents Available\n\n"
                    "You can delegate specialized tasks to these external agents:\n\n"
                    + "\n".join(a2a_descriptions)
                    + "\n\nWhen a user request matches an external agent's skills, "
                    "delegate to that agent using the corresponding tool. "
                    "After delegation, use the agent's response to answer the user."
                ),
            }

            # Append to existing messages
            messages = list(messages) + [a2a_system_prompt]
            _logger.info(
                "Added A2A capability prompt: %d agents",
                len(self.a2a_agent_ids),
            )

        return messages
