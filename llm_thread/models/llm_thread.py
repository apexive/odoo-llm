import functools
import json
import logging

import emoji
import markdown2

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.llm_mail_message_subtypes.const import (
    LLM_ASSISTANT_SUBTYPE_XMLID,
    LLM_TOOL_RESULT_SUBTYPE_XMLID,
    LLM_USER_SUBTYPE_XMLID,
)

_logger = logging.getLogger(__name__)


def execute_with_new_cursor(func_to_decorate):
    """Decorator to execute a method within a new, immediately committed cursor context.

    It injects the browsed record from the new environment as the first argument
    after 'self'. Assumes the decorated method is called on a singleton recordset.
    """

    @functools.wraps(func_to_decorate)
    def wrapper(self, *args, **kwargs):
        self.ensure_one()
        with self.pool.cursor() as cr:
            env = api.Environment(cr, self.env.uid, self.env.context)
            record_in_new_env = env[self._name].browse(self.ids)
            return func_to_decorate(self, record_in_new_env, *args, **kwargs)

    return wrapper


class LLMThread(models.Model):
    _name = "llm.thread"
    _description = "LLM Chat Thread"
    _inherit = ["mail.thread"]
    _order = "write_date DESC"

    name = fields.Char(
        string="Title",
        required=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="User",
        default=lambda self: self.env.user,
        required=True,
        ondelete="restrict",
    )
    provider_id = fields.Many2one(
        "llm.provider",
        string="Provider",
        required=True,
        ondelete="restrict",
    )
    model_id = fields.Many2one(
        "llm.model",
        string="Model",
        required=True,
        domain="[('provider_id', '=', provider_id), ('model_use', 'in', ['chat', 'multimodal'])]",
        ondelete="restrict",
    )
    active = fields.Boolean(default=True)
    message_ids = fields.One2many(
        comodel_name="mail.message",
        inverse_name="res_id",
        string="Messages",
        domain=lambda self: [("model", "=", self._name)],
    )

    # Updated fields for related record reference
    model = fields.Char(
        string="Related Document Model",
        help="Technical name of the related model"
    )
    res_id = fields.Many2oneReference(
        string="Related Document ID",
        model_field="model",
        help="ID of the related record"
    )

    # Computed Reference field for related record
    # TODO: the selection should be removed - ti is computed every time we access the model
    related_record = fields.Reference(
        selection='_get_related_record_selection',
        string='Related Record',
        compute='_compute_related_record',
        readonly=True,
        help="The record this chat thread is related to"
    )

    is_locked = fields.Boolean(
        string="Locked, Preventing Concurrent Generation",
        default=False,
        readonly=True,
        copy=False,
        help="Indicates if the thread is currently locked to prevent concurrent generation.",
    )

    tool_ids = fields.Many2many(
        "llm.tool",
        string="Available Tools",
        help="Tools that can be used by the LLM in this thread",
    )

    @api.model
    def _get_related_record_selection(self):
        """Get the selection options for the Reference field dynamically.

        Returns all available models in the system.
        """
        models = self.env['ir.model'].sudo().search([])
        return [(model.model, model.name) for model in models]

    @api.depends('model', 'res_id')
    def _compute_related_record(self):
        """Compute the related record reference."""
        for record in self:
            if record.model and record.res_id:
                # Validate that the model exists and the record exists
                try:
                    if record.model in self.env:
                        related_record = self.env[record.model].browse(record.res_id)
                        if related_record.exists():
                            record.related_record = f"{record.model},{record.res_id}"
                        else:
                            record.related_record = False
                    else:
                        record.related_record = False
                except Exception as e:
                    _logger.warning(f"Error computing related record for thread {record.id}: {e}")
                    record.related_record = False
            else:
                record.related_record = False

    @api.model_create_multi
    def create(self, vals_list):
        """Set default title if not provided"""
        for vals in vals_list:
            if not vals.get("name"):
                vals["name"] = f"Chat with {self.model_id.name}"
        return super().create(vals_list)

    def _post_message(self, **kwargs):
        self.ensure_one()
        # if subtype_xmlid is not provided or wrong,message_post automatically
        # uses the default subtype
        subtype_xmlid = kwargs.get("subtype_xmlid")
        author_id = kwargs.get("author_id")
        body = kwargs.get("body", "")
        email_from = self.get_email_from(
            self.sudo().provider_id.name,
            self.sudo().model_id.name,
            subtype_xmlid,
            author_id,
            kwargs.get("tool_name"),
        )
        post_vals = self.build_post_vals(subtype_xmlid, body, author_id, email_from)
        message = self.message_post(**post_vals)
        extra_vals = self.build_update_vals(**kwargs)
        if extra_vals:
            message.write(extra_vals)
        return message

    def _get_message_history_recordset(self, order="ASC", limit=None):
        """Get messages from the thread

        Args:
            order: Optional order for messages ('ASC' or 'DESC')
            limit: Optional limit on number of messages to retrieve

        Returns:
            mail.message recordset containing the messages
        """
        self.ensure_one()
        subtypes_to_fetch = [
            self.env.ref(LLM_USER_SUBTYPE_XMLID, raise_if_not_found=False),
            self.env.ref(LLM_ASSISTANT_SUBTYPE_XMLID, raise_if_not_found=False),
            self.env.ref(LLM_TOOL_RESULT_SUBTYPE_XMLID, raise_if_not_found=False),
        ]
        subtype_ids = [st.id for st in subtypes_to_fetch if st]

        # Default to descending order to get the most recent messages
        order_clause = "create_date DESC, write_date DESC, id DESC"
        domain = [
            ("model", "=", self._name),
            ("res_id", "=", self.id),
            ("message_type", "=", "comment"),
            ("subtype_id", "in", subtype_ids),
        ]

        # Fetch messages (most recent first)
        messages = self.env["mail.message"].search(
            domain, order=order_clause, limit=limit
        )

        if order == "ASC":
            messages = messages[::-1]

        return messages

    def _get_last_message_from_history(self):
        """Get the last message from the message history."""
        self.ensure_one()
        last_message = None
        result = self._get_message_history_recordset(order="DESC", limit=1)
        if result:
            last_message = result[0]
        if not last_message:
            raise UserError("No message found to process.")
        return last_message

    def _init_message(self, user_message_body, **kwargs):
        """Initialize first message: user input or history."""
        if user_message_body:
            return self._post_message(
                subtype_xmlid=LLM_USER_SUBTYPE_XMLID,
                body=user_message_body,
                author_id=self.env.user.partner_id.id,
                **kwargs,
            )
        return self._get_last_message_from_history()

    def _should_continue(self, last_message):
        """Whether to keep looping on the last_message."""
        if not last_message:
            return False
        if (
                last_message.is_llm_user_message()
                or last_message.is_llm_tool_result_message()
        ):
            return True
        if last_message.is_llm_assistant_message() and last_message.tool_calls:
            return True
        return False

    def _next_step(self, last_message):
        """Dispatch to the next generator based on message type."""
        if (
                last_message.is_llm_user_message()
                or last_message.is_llm_tool_result_message()
        ):
            return self._get_assistant_response()
        if last_message.is_llm_assistant_message() and last_message.tool_calls:
            return self._process_tool_calls(last_message)
        return last_message

    def generate(self, user_message_body, **kwargs):
        self.ensure_one()
        if self.is_locked:
            raise UserError(
                _("This thread is already generating a response. Please wait.")
            )
        self._lock()

        try:
            # orchestrate via hooks
            last = self._init_message(user_message_body, **kwargs)
            if user_message_body:
                yield {"type": "message_create", "message": last.message_format()[0]}
            while self._should_continue(last):
                last = yield from self._next_step(last)
            return last
        finally:
            self._unlock()

    def _process_tool_calls(self, assistant_msg):
        self.ensure_one()
        defs = json.loads(assistant_msg.tool_calls or "[]")
        last_tool_msg = None
        for tool_def in defs:
            last_tool_msg = yield from self.env["mail.message"].stream_llm_tool_result(
                thread=self,
                tool_call_def=tool_def,
            )
        return last_tool_msg

    def get_prepend_messages(self):
        """Hook: return a list of formatted messages to prepend to the conversation.
        Override in other modules if needed.

        Returns:
            list: List of message dictionaries in the format:
                [{"role": "system", "content": "..."},
                 {"role": "user", "content": "..."},
                 ...]
        """
        return []

    def _get_assistant_response(self):
        self.ensure_one()
        message_history_rs = self._get_message_history_recordset()
        tool_rs = self.tool_ids
        chat_kwargs = {
            "messages": message_history_rs,
            "tools": tool_rs,
            "stream": True,
            "prepend_messages": self.get_prepend_messages(),
        }
        stream_response = self.sudo().model_id.chat(**chat_kwargs)
        assistant_msg = yield from self.env["mail.message"].create_message_from_stream(
            self,
            stream_response,
            LLM_ASSISTANT_SUBTYPE_XMLID,
            placeholder_text="Thinking...",
        )
        return assistant_msg

    def _execute_tool(self, tool_name, arguments_str):
        """Execute a tool and return the result."""
        self.ensure_one()
        tool = self.tool_ids.filtered(lambda t: t.name == tool_name)[:1]
        if not tool:
            raise UserError(f"Tool '{tool_name}' not found in this thread")
        arguments = json.loads(arguments_str)
        return tool.execute(arguments)

    def _lock(self):
        """Acquires a lock on the thread, ensuring immediate commit."""
        self.ensure_one()
        if self._read_is_locked_decorated():
            raise UserError(
                _(
                    "Lock Error: This thread is already generating a response. Please wait."
                )
            )
        self._write_vals_decorated({"is_locked": True})

    def _unlock(self):
        """Releases the lock on the thread, ensuring immediate commit."""
        self.ensure_one()
        if self._read_is_locked_decorated():
            self._write_vals_decorated({"is_locked": False})

    @execute_with_new_cursor
    def _read_is_locked_decorated(self, record_in_new_env):
        """Reads the 'is_locked' status using a new cursor."""
        return record_in_new_env.is_locked

    @execute_with_new_cursor
    def _write_vals_decorated(self, record_in_new_env, vals):
        """Writes values using a new, immediately committed cursor."""
        return record_in_new_env.write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_llm_thread(self):
        unlink_ids = [record.id for record in self]
        self.env["bus.bus"]._sendone(
            self.env.user.partner_id, "llm.thread/delete", {"ids": unlink_ids}
        )

    def get_context(self, base_context=None):
        return base_context or {}

    @api.model
    def get_email_from(
            self,
            provider_name,
            provider_model_name,
            subtype_xmlid,
            author_id,
            tool_name=None,
    ):
        if not author_id:
            if subtype_xmlid == LLM_TOOL_RESULT_SUBTYPE_XMLID:
                name = tool_name or "Tool"
                return f"{name} <tool@{provider_name.lower().replace(' ', '')}.ai>"
            elif subtype_xmlid == LLM_ASSISTANT_SUBTYPE_XMLID:
                model = provider_model_name or "Assistant"
                provider = provider_name.lower().replace(" ", "")
                return f"{model} <ai@{provider}.ai>"
        return None

    @api.model
    def build_post_vals(self, subtype_xmlid, body, author_id, email_from):
        return {
            "body": markdown2.markdown(emoji.demojize(body)),
            "message_type": "comment",
            "subtype_xmlid": subtype_xmlid,
            "author_id": author_id,
            "email_from": email_from or None,
            "partner_ids": [],
        }

    @api.model
    def build_update_vals(
            self,
            subtype_xmlid,
            tool_call_id=None,
            tool_calls=None,
            tool_call_definition=None,
            tool_call_result=None,
            **kwargs,
    ):
        if subtype_xmlid == LLM_ASSISTANT_SUBTYPE_XMLID and tool_calls:
            return {"tool_calls": tool_calls}
        if subtype_xmlid == LLM_TOOL_RESULT_SUBTYPE_XMLID:
            vals = {
                "tool_call_id": tool_call_id,
                "tool_call_definition": tool_call_definition,
                "tool_call_result": tool_call_result,
            }
            return {k: v for k, v in vals.items() if v is not None}

    @api.model
    def get_thread_from_context(self):
        """
        Try to get the llm.thread from the context.
        This is useful when the template is used in a thread context.

        Returns:
            llm.thread recordset or False
        """
        _logger.info("Attempting to get thread from context")

        # Check if we have a thread_id in the context
        thread_id = self.env.context.get("thread_id", False)
        if thread_id:
            _logger.info("Found thread_id in context: %s", thread_id)
            thread = self.env["llm.thread"].browse(thread_id).exists()
            if thread:
                _logger.info("Thread exists: %s", thread.name)
                return thread
            else:
                _logger.warning("Thread with ID %s not found", thread_id)
                return False

        return False
