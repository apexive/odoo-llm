import inspect
import json
import logging
from typing import Any, get_type_hints

from pydantic import create_model

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class LLMTool(models.Model):
    _name = "llm.tool"
    _description = "LLM Tool"
    _inherit = ["mail.thread"]

    # Basic tool information
    name = fields.Char(
        required=True,
        tracking=True,
        help="The name of the tool. This will be used by the LLM to call the tool.",
    )
    description = fields.Text(
        required=True,
        tracking=True,
        help="A human-readable description of what the tool does. This will be sent to the LLM.",
    )
    implementation = fields.Selection(
        selection=lambda self: self._selection_implementation(),
        required=True,
        help="The implementation that provides this tool's functionality",
    )
    active = fields.Boolean(default=True)

    # Input schema
    input_schema = fields.Text(
        string="Input Schema",
        help="JSON Schema defining the expected parameters for the tool",
    )

    # Annotations (following the schema specification)
    title = fields.Char(string="Title", help="A human-readable title for the tool")
    read_only_hint = fields.Boolean(
        string="Read Only",
        default=False,
        help="If true, the tool does not modify its environment",
    )
    idempotent_hint = fields.Boolean(
        string="Idempotent",
        default=False,
        help="If true, calling the tool repeatedly with the same arguments will have no additional effect",
    )
    destructive_hint = fields.Boolean(
        string="Destructive",
        default=True,
        help="If true, the tool may perform destructive updates to its environment",
    )
    open_world_hint = fields.Boolean(
        string="Open World",
        default=True,
        help="If true, this tool may interact with an 'open world' of external entities",
    )

    # Implementation-specific fields
    server_action_id = fields.Many2one(
        "ir.actions.server",
        string="Related Server Action",
        help="The specific server action this tool will execute",
    )

    # Function implementation fields
    decorator_model = fields.Char(
        string="Decorator Model",
        readonly=True,
        help="Model name where the decorated method lives (e.g., 'sale.order'). "
        "Set automatically during registration.",
    )
    decorator_method = fields.Char(
        string="Decorator Method",
        readonly=True,
        help="Method name of the decorated tool (e.g., 'create_sales_quote'). "
        "Set automatically during registration.",
    )

    # User consent
    requires_user_consent = fields.Boolean(
        default=False,
        help="If true, the user must consent to the execution of this tool",
    )

    # Default tool flag
    default = fields.Boolean(
        default=False,
        help="Set to true if this is a default tool to be included in all LLM requests",
    )

    # Auto-update flag for function tools
    auto_update = fields.Boolean(
        default=True,
        help="If true, tool metadata will be automatically updated from decorator on Odoo restart. "
        "Set to false to manually manage this tool's configuration.",
    )

    _sql_constraints = [
        (
            "unique_function_tool",
            "UNIQUE(decorator_model, decorator_method)",
            "A tool for this model and method combination already exists!",
        ),
        (
            "unique_tool_name",
            "UNIQUE(name)",
            "A tool with this name already exists! Tool names must be unique.",
        ),
    ]

    @api.model
    def _selection_implementation(self):
        """Get all available implementations from tool implementations"""
        implementations = []
        for implementation in self._get_available_implementations():
            implementations.append(implementation)
        return implementations

    @api.model
    def _get_available_implementations(self):
        """Hook method for registering tool services"""
        return [
            ("function", "Function"),
        ]

    def get_pydantic_model_from_signature(self, method):
        """Create a Pydantic model from a method signature"""
        type_hints = get_type_hints(method)
        signature = inspect.signature(method)
        fields = {}

        for param_name, param in signature.parameters.items():
            if param_name == "self":
                continue
            fields[param_name] = (
                type_hints.get(param_name, Any),
                param.default if param.default != param.empty else ...,
            )

        return create_model("DynamicModel", **fields)

    def _get_decorated_method(self):
        """Get the actual decorated method for function tools"""
        self.ensure_one()

        if not self.decorator_model or not self.decorator_method:
            raise ValueError(
                f"Function tool {self.name} missing decorator_model or decorator_method"
            )

        # Get the model (let KeyError propagate if model doesn't exist)
        model_obj = self.env[self.decorator_model]
        model_class = type(model_obj)

        # Check the method exists on the class
        if not hasattr(model_class, self.decorator_method):
            raise AttributeError(
                f"Method {self.decorator_method} not found on model {self.decorator_model}"
            )

        # Return bound method from the instance (not unbound from class)
        return getattr(model_obj, self.decorator_method)

    def get_input_schema(self):
        """Get input schema - from stored field or generate from method signature

        Returns the tool's input schema. Priority:
        1. Use self.input_schema if set (manual override or stored from decorator)
        2. Generate from method signature using MCP SDK
        """
        self.ensure_one()

        # If schema is stored in DB, use it
        if self.input_schema:
            return json.loads(self.input_schema)

        # Generate schema from method signature
        method_func = self._get_implementation_method()

        # Use MCP SDK's func_metadata to generate proper schema
        from mcp.server.fastmcp.utilities.func_metadata import func_metadata

        func_meta = func_metadata(method_func)

        # Get MCP-compatible schema
        schema = func_meta.arg_model.model_json_schema(by_alias=True)
        return schema

    def execute(self, parameters):
        """Execute this tool with validated parameters"""
        # Get the actual method to execute
        method = self._get_implementation_method()

        # Validate parameters against method signature
        model = self.get_pydantic_model_from_signature(method)
        validated = model(**parameters)

        # Execute the method
        return method(**validated.model_dump())

    def _get_implementation_method(self):
        """Get the actual method for this tool's implementation"""
        self.ensure_one()

        if self.implementation == "function":
            # For decorated tools, get the actual decorated method
            method = self._get_decorated_method()

            # Validate it's actually decorated (optional safety check)
            if not getattr(method, "_is_llm_tool", False):
                _logger.warning(
                    "Method '%s' on model '%s' is not decorated with @llm_tool",
                    self.decorator_method,
                    self.decorator_model,
                )

            return method
        else:
            # For other future implementations, use {implementation}_execute pattern
            impl_method_name = f"{self.implementation}_execute"
            if not hasattr(self, impl_method_name):
                raise NotImplementedError(
                    _("Implementation method %(method)s not found")
                    % {"method": impl_method_name}
                )
            return getattr(self, impl_method_name)

    # In-memory registries, populated by _register_hook (no DB access).
    _tool_registry = {}  # {(model_name, method_name): values_dict}
    _xml_managed_keys = set()  # {(model_name, method_name)} for xml-managed tools

    @staticmethod
    def _extract_tool_values(model_name, method_name, method):
        """Build values dict from decorator metadata. No DB access."""
        tool_name = getattr(method, "_llm_tool_name", method_name)
        values = {
            "name": tool_name,
            "implementation": "function",
            "decorator_model": model_name,
            "decorator_method": method_name,
            "description": getattr(method, "_llm_tool_description", ""),
            "active": True,
        }
        metadata = getattr(method, "_llm_tool_metadata", {})
        for hint in (
            "read_only_hint",
            "idempotent_hint",
            "destructive_hint",
            "open_world_hint",
        ):
            if hint in metadata:
                values[hint] = metadata[hint]
        if hasattr(method, "_llm_tool_schema"):
            values["input_schema"] = json.dumps(method._llm_tool_schema, indent=2)
        return values

    # ------------------------------------------------------------------
    # Registration: _register_hook (scan) → _sync_tools_to_db (raw SQL)
    # ------------------------------------------------------------------

    @api.model
    def _register_hook(self):
        """Scan for @llm_tool decorated methods and sync to DB."""
        super()._register_hook()
        self._scan_tool_decorators()
        self._sync_tools_to_db()

    def _scan_tool_decorators(self):
        """Populate _tool_registry from @llm_tool decorated methods."""
        self._tool_registry.clear()
        self._xml_managed_keys.clear()

        for model_name in self.env.registry:
            try:
                model = self.env[model_name]
            except Exception:
                continue

            model_class = type(model)
            for attr_name in dir(model_class):
                if attr_name.startswith("_"):
                    continue
                try:
                    attr = getattr(model_class, attr_name, None)
                    if callable(attr) and getattr(attr, "_is_llm_tool", False):
                        key = (model_name, attr_name)
                        if getattr(attr, "_llm_tool_xml_managed", False):
                            self._xml_managed_keys.add(key)
                        else:
                            self._tool_registry[key] = self._extract_tool_values(
                                model_name, attr_name, attr
                            )
                except Exception:
                    continue

    @staticmethod
    def _raw_values_changed(db_row, values):
        """Compare in-memory values dict with a raw DB row dict."""
        _skip = {"implementation", "decorator_model", "decorator_method"}
        for key, new_val in values.items():
            if key in _skip:
                continue
            db_val = db_row.get(key)
            # Treat None/False/"" as equivalent
            if not db_val and not new_val:
                continue
            if db_val != new_val:
                return True
        return False

    @api.model
    def _sync_tools_to_db(self):
        """Sync _tool_registry → DB via raw SQL.

        Acquires a database-specific advisory lock so exactly one worker
        performs the write.  Raw SQL bypasses the ORM cache, which avoids
        the SerializationFailure that occurs when load_modules calls
        flush_all() with dirty ORM state from concurrent workers.

        Called automatically from _register_hook on every startup, and
        can also be triggered manually via the "Sync Tools" button.

        Returns dict: {created: int, updated: int, deactivated: int}.
        """
        cr = self.env.cr

        # Database-specific advisory lock (transaction-scoped, auto-released)
        lock_key = hash(cr.dbname) & 0x7FFFFFFF
        cr.execute("SELECT pg_try_advisory_xact_lock(%s)", [lock_key])
        if not cr.fetchone()[0]:
            _logger.debug("Another worker is syncing tools, skipping")
            return {"created": 0, "updated": 0, "deactivated": 0}

        if not self._tool_registry:
            return {"created": 0, "updated": 0, "deactivated": 0}

        # Read existing function tools via raw SQL (bypasses ORM cache)
        cr.execute(
            "SELECT id, name, decorator_model, decorator_method, description,"
            "       active, auto_update, read_only_hint, idempotent_hint,"
            "       destructive_hint, open_world_hint, input_schema"
            "  FROM llm_tool"
            " WHERE implementation = 'function'"
        )
        existing_by_key = {}
        for row in cr.dictfetchall():
            existing_by_key[(row["decorator_model"], row["decorator_method"])] = row

        now = fields.Datetime.now()
        uid = self.env.uid or 1
        created = updated = deactivated = 0

        for key, values in self._tool_registry.items():
            db_row = existing_by_key.pop(key, None)
            if db_row:
                if db_row["auto_update"] and self._raw_values_changed(db_row, values):
                    cr.execute(
                        "UPDATE llm_tool"
                        "   SET name = %s, description = %s, active = %s,"
                        "       read_only_hint = %s, idempotent_hint = %s,"
                        "       destructive_hint = %s, open_world_hint = %s,"
                        "       input_schema = %s,"
                        "       write_date = %s, write_uid = %s"
                        " WHERE id = %s",
                        [
                            values["name"],
                            values.get("description", ""),
                            values.get("active", True),
                            values.get("read_only_hint", db_row["read_only_hint"]),
                            values.get("idempotent_hint", db_row["idempotent_hint"]),
                            values.get("destructive_hint", db_row["destructive_hint"]),
                            values.get("open_world_hint", db_row["open_world_hint"]),
                            values.get("input_schema", db_row["input_schema"]),
                            now,
                            uid,
                            db_row["id"],
                        ],
                    )
                    updated += 1
            else:
                cr.execute(
                    "INSERT INTO llm_tool"
                    "  (name, implementation, decorator_model, decorator_method,"
                    "   description, active, auto_update,"
                    "   read_only_hint, idempotent_hint,"
                    "   destructive_hint, open_world_hint,"
                    "   input_schema,"
                    "   create_date, write_date, create_uid, write_uid)"
                    " VALUES (%s, 'function', %s, %s, %s, %s, true,"
                    "         %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    [
                        values["name"],
                        values["decorator_model"],
                        values["decorator_method"],
                        values.get("description", ""),
                        values.get("active", True),
                        values.get("read_only_hint", False),
                        values.get("idempotent_hint", False),
                        values.get("destructive_hint", True),
                        values.get("open_world_hint", True),
                        values.get("input_schema"),
                        now,
                        now,
                        uid,
                        uid,
                    ],
                )
                created += 1

        # Deactivate function tools no longer in registry (skip xml-managed)
        for key, db_row in existing_by_key.items():
            if db_row["active"] and key not in self._xml_managed_keys:
                cr.execute(
                    "UPDATE llm_tool SET active = false,"
                    "       write_date = %s, write_uid = %s"
                    " WHERE id = %s",
                    [now, uid, db_row["id"]],
                )
                deactivated += 1

        if created or updated or deactivated:
            self.invalidate_model()
            _logger.info(
                "Tool sync: %d created, %d updated, %d deactivated",
                created,
                updated,
                deactivated,
            )

        return {"created": created, "updated": updated, "deactivated": deactivated}

    # ------------------------------------------------------------------
    # UI action: manual sync button on list view
    # ------------------------------------------------------------------

    def action_sync_tools(self):
        """Manual sync button — wraps _sync_tools_to_db with UI notification."""
        Tool = self.env["llm.tool"]
        if not Tool._tool_registry:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Nothing to sync"),
                    "message": _("Tool registry is empty. Restart the server first."),
                    "type": "warning",
                    "sticky": False,
                },
            }

        result = Tool._sync_tools_to_db()
        if not any(result.values()):
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Already in sync"),
                    "message": _("All tools are up to date."),
                    "type": "info",
                    "sticky": False,
                },
            }

        parts = []
        if result["created"]:
            parts.append(_("%d created", result["created"]))
        if result["updated"]:
            parts.append(_("%d updated", result["updated"]))
        if result["deactivated"]:
            parts.append(_("%d deactivated", result["deactivated"]))

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Tools synced"),
                "message": ", ".join(str(p) for p in parts),
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.client", "tag": "reload"},
            },
        }

    # API methods for the Tool schema
    def get_tool_definition(self):
        """Returns MCP-compatible tool definition"""
        self.ensure_one()

        # For function tools, use docstring if no description in DB
        description = self.description
        if self.implementation == "function" and not description:
            try:
                method = self._get_decorated_method()
                description = inspect.getdoc(method) or ""
            except (ValueError, AttributeError, KeyError):
                pass  # Could not get method, use empty description

        # Get the input schema (respects stored field or generates)
        input_schema_data = self.get_input_schema()

        # Create MCP ToolAnnotations (only with non-None values)
        from mcp.types import Tool, ToolAnnotations

        # Build annotations dict with only non-None values
        annotations_data = {}
        if self.read_only_hint is not None:
            annotations_data["readOnlyHint"] = self.read_only_hint
        if self.idempotent_hint is not None:
            annotations_data["idempotentHint"] = self.idempotent_hint
        if self.destructive_hint is not None:
            annotations_data["destructiveHint"] = self.destructive_hint
        if self.open_world_hint is not None:
            annotations_data["openWorldHint"] = self.open_world_hint

        tool_annotations = (
            ToolAnnotations(**annotations_data) if annotations_data else None
        )

        # Create and validate MCP Tool instance
        mcp_tool = Tool(
            name=self.name,
            title=self.title
            if self.title
            else self.name,  # title goes to BaseMetadata, not ToolAnnotations
            description=self.description or "",
            inputSchema=input_schema_data,
            annotations=tool_annotations,
        )

        # Return plain dict following 'Models Return Plain Data' pattern
        return mcp_tool.model_dump(exclude_none=True)

    @api.onchange("implementation")
    def _onchange_implementation(self):
        """When implementation changes and input_schema is empty, populate it with the implementation schema"""
        if self.implementation and not self.input_schema:
            schema = self.get_input_schema()
            if schema:
                self.input_schema = json.dumps(schema, indent=2)

    def action_reset_input_schema(self):
        """Reset the input schema to the implementation schema"""
        for record in self:
            # Temporarily clear input_schema to force regeneration
            old_schema = record.input_schema
            record.input_schema = False
            try:
                schema = record.get_input_schema()
                if schema:
                    record.input_schema = json.dumps(schema, indent=2)
                else:
                    # If no schema generated, restore old one
                    record.input_schema = old_schema
            except Exception:
                # If regeneration fails, restore old schema and propagate error
                record.input_schema = old_schema
                raise
        # Return an action to reload the view
        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }
