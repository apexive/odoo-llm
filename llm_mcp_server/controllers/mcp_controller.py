"""
MCP Server Controller for Odoo

Ultra-thin HTTP controller that routes requests to appropriate Odoo models
following proper separation of concerns.
"""

import json
import logging
from http import HTTPStatus
from typing import Optional

import werkzeug.exceptions
from mcp.types import InitializeResult
from pydantic import BaseModel

from odoo import http
from odoo.http import request

from ..mcp_json_dispatcher import MCPMethodNotFoundError

_logger = logging.getLogger(__name__)

# MCP SDK Constants
CONTENT_TYPE_JSON = "application/json"
MCP_SESSION_ID_HEADER = "Mcp-Session-Id"
MCP_PROTOCOL_VERSION_HEADER = "Mcp-Protocol-Version"


class MCPInitializeResponse(BaseModel):
    """Wrapper for MCP initialize method response"""

    result: InitializeResult
    session_id: Optional[str] = None


def requires_bearer_auth(handler_func):
    """Decorator that applies MCP-compatible bearer authentication"""

    def wrapper(self, *args, **kwargs):
        # Clean up the public uid and use built-in _auth_method_bearer
        request.update_env(user=False)
        request.env["ir.http"]._auth_method_bearer()

        # Authentication succeeded - proceed with handler
        return handler_func(self, *args, **kwargs)

    return wrapper


class MCPController(http.Controller):
    """
    Ultra-thin MCP Server Controller following Odoo best practices.

    This controller delegates all business logic to Odoo models:
    - Config model handles initialize and server configuration
    - Tool model handles tools/list and tools/call
    """

    @http.route(
        "/mcp", type="mcp_json", auth="public", methods=["POST"], csrf=False, cors="*"
    )
    def mcp_endpoint(self, **params):
        """MCP endpoint for JSON-RPC methods using custom dispatcher"""
        # Extract data from JSON-RPC request via dispatcher
        method = request.dispatcher.jsonrequest.get("method")
        request_id = request.dispatcher.request_id
        params = request.params or {}

        # Check if method handler exists
        if not self._is_callable(method):
            raise MCPMethodNotFoundError(method)

        # Dispatch to appropriate handler
        dispatch_result = self._dispatch(method, params, request_id)

        # Handle special case for notifications that return HTTP Response directly
        if isinstance(dispatch_result, http.Response):
            return dispatch_result

        # Handle MCPInitializeResponse wrapper (from initialize method)
        if isinstance(dispatch_result, MCPInitializeResponse):
            result = dispatch_result.result
            session_id = dispatch_result.session_id
            # Store session_id for header response
            if session_id:
                request.mcp_session_id = session_id
        else:
            # All other methods return result directly
            result = dispatch_result

        # Convert pydantic result object to dict.
        # by_alias=True is required: mcp >= 2.0 renamed the model fields to
        # snake_case and keeps the MCP wire names as aliases, so a plain
        # model_dump() would serialise every response ("initialize",
        # "tools/list", "tools/call") with the wrong keys. Correct on 1.x too.
        if hasattr(result, "model_dump"):
            return result.model_dump(by_alias=True, exclude_none=True)
        else:
            return result or {}

    @http.route("/mcp", type="http", auth="bearer", methods=["DELETE"], csrf=False)
    def mcp_delete_session(self):
        """MCP endpoint for session termination"""
        return self._handle_delete_session()

    def _handle_delete_session(self):
        """Handle DELETE request for session termination"""
        session_id = request.httprequest.headers.get("mcp-session-id")

        if not session_id:
            return http.Response(
                "Missing mcp-session-id header",
                status=HTTPStatus.BAD_REQUEST,  # Bad Request
            )

        # Find session using the model's get_session method
        session = request.env["llm.mcp.session"].get_session(session_id)

        if not session:
            return http.Response(
                "Session not found",
                status=HTTPStatus.NOT_FOUND,  # Not Found
            )

        session.terminate()
        return http.Response("", status=HTTPStatus.NO_CONTENT)  # No Content

    # MCP Method Handlers
    def _mcp_initialize(self, params, request_id):
        """Handle initialize method with protocol version validation"""
        config = request.env["llm.mcp.server.config"].sudo().get_active_config()

        # Extract protocol version from headers or params
        requested_version = request.httprequest.headers.get(
            MCP_PROTOCOL_VERSION_HEADER
        ) or params.get("protocolVersion")

        # Use default if no version requested
        negotiated_version = requested_version or config.get_default_protocol_version()

        # Get server response using the negotiated version
        result = config.handle_initialize_request(
            client_info=params.get("clientInfo"), protocol_version=negotiated_version
        )
        # For stateful mode, create new session
        if config.mode == "stateful":
            session = request.env["llm.mcp.session"].sudo().create_new_session()

            # Store client information in session
            if params.get("clientInfo"):
                session.client_info = params["clientInfo"]
            if params.get("capabilities"):
                session.client_capabilities = params["capabilities"]
            # Store the negotiated protocol version
            session.protocol_version = negotiated_version

            # Transition to initializing state
            session.transition_to("initializing")

            # Return wrapped response with session_id
            return MCPInitializeResponse(result=result, session_id=session.session_id)

        # For stateless mode, return wrapped response without session_id
        return MCPInitializeResponse(result=result)

    def _mcp_notifications_initialized(self, params, request_id):
        """Handle notifications/initialized method"""
        # Get session ID from headers (validated by dispatcher)
        session_id = request.httprequest.headers.get("mcp-session-id")

        # Get session and transition to initialized state
        if session_id:
            session = request.env["llm.mcp.session"].sudo().get_session(session_id)

            if session and session.state == "initializing":
                session.transition_to("initialized")
                # Force immediate commit so concurrent requests see the updated state
                session._cr.commit()

        # For JSON-RPC notifications, use werkzeug.abort to bypass JSON-RPC entirely
        # Following Odoo's pattern from http.py line 2185 (and 2330 & 2333)
        werkzeug.exceptions.abort(
            http.Response(
                "",
                headers={"Content-Type": CONTENT_TYPE_JSON},
                status=HTTPStatus.ACCEPTED,
            )
        )

    def _mcp_ping(self, params, request_id):
        """Handle ping method"""
        return {}

    @requires_bearer_auth
    def _mcp_tools_list(self, params, request_id):
        """Handle tools/list method"""
        return request.env["llm.tool"].get_mcp_tools_list(params=params)

    @requires_bearer_auth
    def _mcp_tools_call(self, params, request_id):
        """Handle tools/call method"""
        # Get session ID from headers if available
        session_id = request.httprequest.headers.get("mcp-session-id")

        # Update session user_id if we have a session and authenticated user
        if session_id and request.env.user and not request.env.user._is_public():
            session = request.env["llm.mcp.session"].get_session(session_id)
            if session and not session.user_id:
                session.user_id = request.env.user.id

        return request.env["llm.tool"].execute_mcp_tool(params=params)

    def _is_callable(self, method_name):
        """Check if method handler exists"""
        handler_name = f"_mcp_{method_name.replace('/', '_').replace('-', '_')}"
        return hasattr(self, handler_name) and callable(getattr(self, handler_name))

    def _dispatch(self, method_name, params, request_id):
        """Dispatch MCP method to appropriate handler"""
        # Transform method name to handler name
        handler_name = f"_mcp_{method_name.replace('/', '_').replace('-', '_')}"

        # Get handler method
        handler = getattr(self, handler_name, None)
        if not handler:
            raise MCPMethodNotFoundError(method_name)

        # Call handler
        return handler(params, request_id)

    @http.route("/mcp/health", type="http", auth="public", methods=["GET", "POST"])
    def health_check(self):
        """Health check endpoint"""
        config = request.env["llm.mcp.server.config"].sudo().get_active_config()
        health_data = config.get_health_status_data()

        return http.Response(
            json.dumps(health_data, indent=2),
            headers={"Content-Type": CONTENT_TYPE_JSON},
            status=HTTPStatus.OK,
        )
