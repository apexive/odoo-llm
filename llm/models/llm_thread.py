from odoo import api, fields, models


class LLMThread(models.Model):
    _name = "llm.thread"
    _description = "LLM Chat Thread"
    _inherit = ["mail.thread"]
    _order = "write_date DESC"

    name = fields.Char(string="Title", required=True)
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
    message_ids = fields.One2many("llm.message", "thread_id", string="Messages")
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        # Set default title if not provided
        for vals in vals_list:
            if not vals.get("name"):
                vals["name"] = f"Chat {fields.Datetime.now()}"
        return super().create(vals_list)

    def get_chat_messages(self, limit=None):
        """Get messages in provider-compatible format"""
        domain = [("thread_id", "=", self.id)]
        messages = self.env["llm.message"].search(
            domain, order="create_date ASC", limit=limit
        )
        return [msg.to_provider_message() for msg in messages]

    def send_message(self, content, role="user"):
        """Send a new message in the thread"""
        self.env["llm.message"].create(
            {
                "thread_id": self.id,
                "content": content,
                "role": role,
            }
        )
        if role == "user":
            # Get AI response
            messages = self.get_chat_messages()
            response = self.provider_id.chat(messages)

            # Save AI response
            self.env["llm.message"].create(
                {
                    "thread_id": self.id,
                    "content": response,
                    "role": "assistant",
                }
            )
        return True


class LLMMessage(models.Model):
    _name = "llm.message"
    _description = "LLM Chat Message"
    _order = "create_date ASC"

    thread_id = fields.Many2one(
        "llm.thread",
        string="Thread",
        required=True,
        ondelete="cascade",
    )
    role = fields.Selection(
        [
            ("system", "System"),
            ("user", "User"),
            ("assistant", "Assistant"),
            ("tool", "Tool"),
        ],
        required=True,
        default="user",
    )
    content = fields.Text(required=True)
    create_date = fields.Datetime(readonly=True)

    def to_provider_message(self):
        """Convert to provider-compatible message format"""
        return {
            "role": self.role,
            "content": self.content,
        }

    @api.model
    def from_provider_message(self, thread_id, message):
        """Create from provider message format"""
        return self.create(
            {
                "thread_id": thread_id,
                "role": message["role"],
                "content": message["content"],
            }
        )
