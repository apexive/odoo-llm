import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class LlmA2aController(http.Controller):
    @http.route("/llm/a2a/agents", type="json", auth="user")
    def get_agents(self, domain=None):
        """Get list of A2A agents for the current user.

        Args:
            domain: Optional domain filter

        Returns:
            List of agent data dicts
        """
        domain = domain or [("state", "=", "connected")]
        agents = request.env["llm.a2a.agent"].search(domain)

        return [
            {
                "id": agent.id,
                "name": agent.name,
                "description": agent.agent_description or "",
                "skills": agent.agent_skills or "",
                "state": agent.state,
                "url": agent.url,
            }
            for agent in agents
        ]

    @http.route("/llm/a2a/agent/<int:agent_id>/test", type="json", auth="user")
    def test_agent(self, agent_id):
        """Test connection to an A2A agent.

        Args:
            agent_id: ID of the agent to test

        Returns:
            dict with success status and message
        """
        agent = request.env["llm.a2a.agent"].browse(agent_id)
        if not agent.exists():
            return {"success": False, "error": "Agent not found"}

        agent._fetch_agent_card()

        return {
            "success": agent.state == "connected",
            "state": agent.state,
            "error": agent.last_error if agent.state == "error" else None,
            "agent_card": agent.agent_card,
        }

    @http.route(
        "/llm/thread/<int:thread_id>/a2a_agents",
        type="json",
        auth="user",
        methods=["POST"],
    )
    def update_thread_agents(self, thread_id, agent_ids):
        """Update the A2A agents assigned to a thread.

        Args:
            thread_id: ID of the thread
            agent_ids: List of agent IDs to assign

        Returns:
            dict with updated thread data
        """
        thread = request.env["llm.thread"].browse(thread_id)
        if not thread.exists():
            return {"success": False, "error": "Thread not found"}

        thread.write({"a2a_agent_ids": [(6, 0, agent_ids)]})

        return {
            "success": True,
            "a2a_agent_ids": [
                {
                    "id": agent.id,
                    "name": agent.name,
                    "description": agent.agent_description or "",
                    "skills": agent.agent_skills or "",
                    "state": agent.state,
                }
                for agent in thread.a2a_agent_ids
            ],
        }
