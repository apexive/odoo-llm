from odoo import api, fields, models


class LLMThread(models.Model):
    _name = "llm.thread"
    _description = "LLM Chat Thread"
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

    def chat(self, content, role="user"):
        """Regular non-streaming chat method"""
        # Save user message
        self.env["llm.message"].create({
            "thread_id": self.id,
            "content": content,
            "role": role,
        })

        if role == "user":
            # Get AI response
            messages = self.get_chat_messages()
            response = self.model_id.chat(messages, stream=False)

            # Save AI response
            self.env["llm.message"].create({
                "thread_id": self.id,
                "content": response,
                "role": "assistant",
            })
        return True

    def chat_stream(self, content, role="user"):
        """Streaming chat method"""
        # Save user message
        self.env["llm.message"].create({
            "thread_id": self.id,
            "content": content,
            "role": role,
        })

        if role == "user":
            # Get AI response with streaming
            messages = self.get_chat_messages()
            response_stream = self.model_id.chat(messages, stream=True)

            # Initialize content accumulator
            accumulated_content = ""

            # Stream response chunks
            for chunk in response_stream:
                accumulated_content += chunk
                yield f'data: {{"content": "{chunk}"}}'

            # End stream
            yield "[DONE]"

            # Save complete response
            self.env["llm.message"].create({
                "thread_id": self.id,
                "content": accumulated_content,
                "role": "assistant",
            })

    def send_message(self, content, role="user", stream=False):
        """Unified message sending interface"""
        if stream:
            return self.chat_stream(content, role)
        return self.chat(content, role)

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

    def to_frontend_data(self):
        """Convert to frontend-friendly format"""
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "timestamp": fields.Datetime.to_string(self.create_date),
            "author": self.get_author_name(),
        }

    def get_author_name(self):
        """Get author name based on role"""
        if self.role == "user":
            return self.thread_id.user_id.name
        elif self.role == "assistant":
            return self.thread_id.model_id.name
        return self.role.title()

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
