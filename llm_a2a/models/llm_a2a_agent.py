import asyncio
import json
import logging
from typing import Any

import httpx

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class LlmA2aAgent(models.Model):
    _name = "llm.a2a.agent"
    _description = "A2A Agent"
    _inherit = ["mail.thread"]

    name = fields.Char(
        required=True,
        tracking=True,
        help="Display name for the agent",
    )
    url = fields.Char(
        required=True,
        tracking=True,
        help="Base URL of the A2A agent (e.g., http://localhost:9999)",
    )
    active = fields.Boolean(default=True)

    # Agent Card information (fetched from remote agent)
    agent_card = fields.Text(
        string="Agent Card (JSON)",
        readonly=True,
        help="The agent's self-describing manifest fetched from the remote agent",
    )
    agent_description = fields.Text(
        string="Description",
        compute="_compute_agent_card_info",
        store=True,
        help="Description from the agent card",
    )
    agent_version = fields.Char(
        string="Version",
        compute="_compute_agent_card_info",
        store=True,
    )
    agent_skills = fields.Text(
        string="Skills",
        compute="_compute_agent_card_info",
        store=True,
        help="Skills/capabilities of this agent",
    )

    # Endpoint type (auto-detected)
    endpoint_type = fields.Selection(
        [
            ("jsonrpc", "JSON-RPC"),
            ("rest", "REST API"),
        ],
        string="Endpoint Type",
        readonly=True,
        help="Auto-detected endpoint type based on agent capabilities.",
    )

    # Authentication
    auth_type = fields.Selection(
        [
            ("none", "No Authentication"),
            ("api_key", "API Key"),
            ("bearer", "Bearer Token"),
        ],
        default="none",
        string="Authentication Type",
    )
    api_key = fields.Char(
        string="API Key / Token",
        help="API key or bearer token for authentication",
    )

    # Status
    state = fields.Selection(
        [
            ("draft", "Not Connected"),
            ("connected", "Connected"),
            ("error", "Error"),
        ],
        default="draft",
        string="Status",
        tracking=True,
    )
    last_error = fields.Text(string="Last Error")
    last_connected = fields.Datetime(string="Last Connected")

    _sql_constraints = [
        ("unique_url", "UNIQUE(url)", "An agent with this URL already exists!"),
    ]

    @api.depends("agent_card")
    def _compute_agent_card_info(self):
        """Extract information from the agent card JSON"""
        for record in self:
            if record.agent_card:
                try:
                    card = json.loads(record.agent_card)
                    record.agent_description = card.get("description", "")
                    record.agent_version = card.get("version", "")
                    skills = card.get("skills", [])
                    if skills:
                        skill_names = [s.get("name", s.get("id", "")) for s in skills]
                        record.agent_skills = ", ".join(skill_names)
                    else:
                        record.agent_skills = ""
                except (json.JSONDecodeError, TypeError):
                    record.agent_description = ""
                    record.agent_version = ""
                    record.agent_skills = ""
            else:
                record.agent_description = ""
                record.agent_version = ""
                record.agent_skills = ""

    def _get_auth_headers(self):
        """Get authentication headers for HTTP requests"""
        self.ensure_one()
        headers = {"Content-Type": "application/json"}

        if self.auth_type == "api_key" and self.api_key:
            headers["X-API-Key"] = self.api_key
        elif self.auth_type == "bearer" and self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        return headers

    def action_fetch_agent_card(self):
        """Fetch the agent card from the remote agent"""
        for record in self:
            record._fetch_agent_card()
        return True

    def _detect_endpoint_type(self, client: httpx.Client, card_data: dict) -> str:
        """Auto-detect endpoint type by probing the agent.

        Strategy:
        1. Check if agent card has 'url' field pointing to specific endpoint
        2. Try HEAD request to /message/send - if exists, it's REST
        3. Default to JSON-RPC
        """
        base_url = self.url.rstrip("/")

        # Check agent card for endpoint hints
        card_url = card_data.get("url", "")
        if "/message/send" in card_url or "/message/stream" in card_url:
            return "rest"

        # Probe REST endpoint
        try:
            probe_response = client.options(
                f"{base_url}/message/send",
                headers=self._get_auth_headers(),
                timeout=5.0,
            )
            if probe_response.status_code in (200, 204, 405):
                # Endpoint exists (405 = Method Not Allowed means endpoint exists but OPTIONS not supported)
                return "rest"
        except httpx.RequestError:
            pass

        # Default to JSON-RPC
        return "jsonrpc"

    def _fetch_agent_card(self):
        """Fetch agent card from the A2A agent endpoint and auto-detect endpoint type"""
        self.ensure_one()

        # A2A uses /.well-known/agent.json for agent card
        agent_card_url = f"{self.url.rstrip('/')}/.well-known/agent.json"

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    agent_card_url,
                    headers=self._get_auth_headers(),
                )
                response.raise_for_status()
                card_data = response.json()

                # Auto-detect endpoint type by checking agent card url field
                # Google ADK uses REST endpoints, others may use JSON-RPC
                detected_type = self._detect_endpoint_type(client, card_data)

                # Use sudo to bypass record rules - users executing tools should
                # be able to trigger agent card refresh
                self.sudo().write(
                    {
                        "agent_card": json.dumps(card_data, indent=2),
                        "endpoint_type": detected_type,
                        "state": "connected",
                        "last_error": False,
                        "last_connected": fields.Datetime.now(),
                    }
                )
                _logger.info(
                    "Successfully fetched agent card from %s (endpoint type: %s)",
                    self.url,
                    detected_type,
                )

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error {e.response.status_code}: {e.response.text}"
            self.sudo().write(
                {
                    "state": "error",
                    "last_error": error_msg,
                }
            )
            _logger.error("Failed to fetch agent card from %s: %s", self.url, error_msg)

        except httpx.RequestError as e:
            error_msg = f"Connection error: {str(e)}"
            self.sudo().write(
                {
                    "state": "error",
                    "last_error": error_msg,
                }
            )
            _logger.error("Failed to connect to agent %s: %s", self.url, error_msg)

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.sudo().write(
                {
                    "state": "error",
                    "last_error": error_msg,
                }
            )
            _logger.exception("Unexpected error fetching agent card from %s", self.url)

    def action_test_connection(self):
        """Test the connection to the A2A agent"""
        self.ensure_one()
        self._fetch_agent_card()

        if self.state == "connected":
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Success"),
                    "message": _("Successfully connected to agent: %s") % self.name,
                    "type": "success",
                    "sticky": False,
                },
            }
        else:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Error"),
                    "message": self.last_error or _("Failed to connect"),
                    "type": "danger",
                    "sticky": True,
                },
            }

    def send_message(self, message_text: str, context_id: str = None) -> dict:
        """Send a message to the A2A agent and get response.

        Args:
            message_text: The message to send
            context_id: Optional context/conversation ID

        Returns:
            dict with response data
        """
        self.ensure_one()

        if self.state != "connected":
            self._fetch_agent_card()
            if self.state != "connected":
                raise UserError(
                    _("Agent %s is not connected. Error: %s")
                    % (self.name, self.last_error)
                )

        # A2A JSON-RPC request format
        payload = {
            "jsonrpc": "2.0",
            "id": fields.Datetime.now().isoformat(),
            "method": "message/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"kind": "text", "text": message_text}],
                    "messageId": f"odoo-{fields.Datetime.now().timestamp()}",
                },
            },
        }

        if context_id:
            payload["params"]["message"]["contextId"] = context_id

        # Determine endpoint URL based on endpoint_type
        if self.endpoint_type == "rest":
            # REST API: send to /message/send endpoint
            endpoint_url = f"{self.url.rstrip('/')}/message/send"
            # For REST, we send just the params, not the full JSON-RPC envelope
            request_payload = payload["params"]
        else:
            # JSON-RPC: send full payload to base URL
            endpoint_url = self.url
            request_payload = payload

        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    endpoint_url,
                    headers=self._get_auth_headers(),
                    json=request_payload,
                )
                response.raise_for_status()
                result = response.json()

                # Update last connected time (use sudo to bypass record rules)
                self.sudo().last_connected = fields.Datetime.now()

                # Parse response based on endpoint type
                if self.endpoint_type == "rest":
                    # REST API returns result directly
                    if isinstance(result, dict) and "error" in result:
                        raise UserError(
                            _("A2A Error: %s") % result["error"].get("message", "Unknown")
                        )
                    return result
                else:
                    # JSON-RPC returns wrapped result
                    if "error" in result:
                        raise UserError(
                            _("A2A Error: %s") % result["error"].get("message", "Unknown")
                        )
                    return result.get("result", {})

        except httpx.HTTPStatusError as e:
            raise UserError(
                _("HTTP error calling agent %s: %s") % (self.name, str(e))
            )
        except httpx.RequestError as e:
            raise UserError(
                _("Connection error calling agent %s: %s") % (self.name, str(e))
            )

    def send_message_streaming(self, message_text: str, context_id: str = None):
        """Send a message and yield streaming response chunks.

        Args:
            message_text: The message to send
            context_id: Optional context/conversation ID

        Yields:
            dict with streaming event data
        """
        self.ensure_one()

        if self.state != "connected":
            self._fetch_agent_card()
            if self.state != "connected":
                raise UserError(
                    _("Agent %s is not connected. Error: %s")
                    % (self.name, self.last_error)
                )

        # A2A JSON-RPC request format
        payload = {
            "jsonrpc": "2.0",
            "id": fields.Datetime.now().isoformat(),
            "method": "message/stream",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"kind": "text", "text": message_text}],
                    "messageId": f"odoo-{fields.Datetime.now().timestamp()}",
                },
            },
        }

        if context_id:
            payload["params"]["message"]["contextId"] = context_id

        # Determine endpoint URL based on endpoint_type
        if self.endpoint_type == "rest":
            # REST API: send to /message/stream endpoint
            endpoint_url = f"{self.url.rstrip('/')}/message/stream"
            # For REST, we send just the params, not the full JSON-RPC envelope
            request_payload = payload["params"]
        else:
            # JSON-RPC: send full payload to base URL
            endpoint_url = self.url
            request_payload = payload

        try:
            with httpx.Client(timeout=300.0) as client:
                with client.stream(
                    "POST",
                    endpoint_url,
                    headers=self._get_auth_headers(),
                    json=request_payload,
                ) as response:
                    response.raise_for_status()

                    # Process SSE stream
                    buffer = ""
                    for chunk in response.iter_text():
                        buffer += chunk
                        while "\n\n" in buffer:
                            event_str, buffer = buffer.split("\n\n", 1)
                            if event_str.startswith("data: "):
                                data_str = event_str[6:]
                                try:
                                    event_data = json.loads(data_str)
                                    yield event_data
                                except json.JSONDecodeError:
                                    _logger.warning(
                                        "Failed to parse SSE data: %s", data_str
                                    )

                # Update last connected time (use sudo to bypass record rules)
                self.sudo().last_connected = fields.Datetime.now()

        except httpx.HTTPStatusError as e:
            raise UserError(
                _("HTTP error streaming from agent %s: %s") % (self.name, str(e))
            )
        except httpx.RequestError as e:
            raise UserError(
                _("Connection error streaming from agent %s: %s") % (self.name, str(e))
            )

    def get_tool_definition(self):
        """Generate a tool definition for delegation to this agent.

        This allows LLM to call this agent as a tool.
        """
        self.ensure_one()

        skills_desc = ""
        if self.agent_skills:
            skills_desc = f" Skills: {self.agent_skills}"

        description = self.agent_description or f"Delegate task to {self.name} agent"
        if skills_desc:
            description += f".{skills_desc}"

        return {
            "name": f"delegate_to_{self.name.lower().replace(' ', '_')}",
            "description": description,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "The task or question to delegate to this agent",
                    },
                },
                "required": ["task"],
            },
        }
