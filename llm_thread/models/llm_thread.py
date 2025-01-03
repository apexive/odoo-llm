import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class LLMThread(models.Model):
    _name = "llm.thread"
    _description = "LLM Chat Thread"
    _inherit = ["mail.thread"]
    _order = "write_date DESC"

    name = fields.Char(
        string="Title",
        required=True,
        tracking=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="User",
        default=lambda self: self.env.user,
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    provider_id = fields.Many2one(
        "llm.provider",
        string="Provider",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    model_id = fields.Many2one(
        "llm.model",
        string="Model",
        required=True,
        domain="[('provider_id', '=', provider_id), ('model_use', 'in', ['chat', 'multimodal'])]",
        ondelete="restrict",
        tracking=True,
    )
    active = fields.Boolean(default=True, tracking=True)
    message_ids = fields.One2many(
        comodel_name="mail.message",
        inverse_name="res_id",
        string="Messages",
        domain=lambda self: [("model", "=", self._name)],
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Set default title if not provided"""
        for vals in vals_list:
            if not vals.get("name"):
                vals["name"] = f"Chat {fields.Datetime.now()}"
        return super().create(vals_list)

    def action_open_chat(self):
        """Open chat in dialog"""
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "llm_chat_dialog",
            "name": f"Chat: {self.name}",
            "params": {
                "thread_id": self.id,
            },
            "target": "new",
        }

    def get_thread_data(self):
        """Get thread data for frontend"""
        self.ensure_one()
        return {
            "id": self.id,
            "name": self.name,
            "messages": [msg.to_frontend_data() for msg in self.message_ids],
            "model": {
                "id": self.model_id.id,
                "name": self.model_id.name,
            },
            "provider": {
                "id": self.provider_id.id,
                "name": self.provider_id.name,
            },
        }

    def post_message(self, content, role="user"):
        """Post a message to the thread"""
        _logger.debug("Posting message - role: %s, content: %s", role, content)

        message = self.env["mail.message"].create(
            {
                "model": self._name,
                "res_id": self.id,
                "body": content,
                "message_type": "comment",
                "llm_role": role,
            }
        )
        return message

    def get_chat_messages(self, limit=None):
        """Get messages in provider-compatible format"""
        domain = [
            ("model", "=", self._name),
            ("res_id", "=", self.id),
            ("message_type", "=", "comment"),
        ]
        messages = self.env["mail.message"].search(
            domain, order="create_date ASC", limit=limit
        )
        return [msg.to_provider_message() for msg in messages]

    def get_assistant_response(self, stream=True):
        """Get streaming response from assistant based on conversation history"""
        try:
            messages = self.get_chat_messages()
            _logger.debug("Getting assistant response for messages: %s", messages)

            content = ""
            for response in self.model_id.chat(messages, stream=stream):
                if response.get("content"):
                    content += response.get("content", "")
                    yield response

            if content:
                _logger.debug("Saving assistant response: %s", content)
                self.post_message(content=content, role="assistant")

        except Exception as e:
            _logger.error("Error getting AI response: %s", str(e))
            yield {"error": str(e)}


class MailMessage(models.Model):
    _inherit = "mail.message"

    llm_role = fields.Selection(
        [
            ("system", "System"),
            ("user", "User"),
            ("assistant", "Assistant"),
            ("tool", "Tool"),
        ],
        default="user",
    )

    def to_provider_message(self):
        """Convert to provider-compatible message format"""
        return {
            "role": self.llm_role,
            "content": self.body,
        }

    def to_frontend_data(self):
        """Convert to frontend-friendly format"""
        data = {
            'id': self.id,
            'role': self.llm_role,
            'content': self.body,
            'timestamp': fields.Datetime.to_string(self.create_date),
        }
        
        # Handle author information
        if self.llm_role == 'assistant':
            # For AI messages, use email_from as author display name
            data['author'] = self.email_from or 'AI Assistant'
            data['author_id'] = False
        else:
            # For user messages, use the actual partner
            if self.author_id:
                data['author'] = self.author_id.name
                data['author_id'] = self.author_id.id
            else:
                data['author'] = self.email_from or 'Unknown'
                data['author_id'] = False
                
        return data

    def get_author_name(self):
        """Get author name based on role"""
        thread = self.env["llm.thread"].browse(self.res_id)
        if self.llm_role == "user":
            return thread.user_id.name
        elif self.llm_role == "assistant":
            return thread.model_id.name
        return self.llm_role.title()
