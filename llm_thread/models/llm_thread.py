import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class LLMThread(models.Model):
    _name = "llm.thread"
    _description = "LLM Chat Thread"

    name = fields.Char(compute="_compute_name", store=True)
    user_id = fields.Many2one("res.users", required=True, ondelete="cascade")
    provider_id = fields.Many2one("llm.provider", required=True, ondelete="restrict")
    model_id = fields.Many2one(
        "llm.model",
        required=True,
        ondelete="restrict",
        domain="[('provider_id', '=', provider_id)]",
    )

    # Reference to the mail thread following mail.message's pattern to store related model name and record id
    res_model = fields.Char("Related Document Model", required=True, index=True)
    res_id = fields.Integer("Related Document ID", required=True, index=True)

    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "unique_user_thread",
            "UNIQUE(user_id, res_model, res_id, active)",
            "Only one active LLM thread per user per record allowed",
        )
    ]

    @api.depends("user_id", "res_model", "res_id")
    def _compute_name(self):
        """Compute display name based on user and referenced record"""
        for thread in self:
            try:
                record = self.env[thread.res_model].browse(thread.res_id).exists()
                record_name = (
                    record.display_name
                    if record
                    else f"{thread.res_model},{thread.res_id}"
                )
                thread.name = f"{thread.user_id.name}'s AI Chat on {record_name}"
            except Exception:
                thread.name = f"AI Chat {thread.id}"

    @api.model
    def _get_thread_domain(self, user_id, model, record_id, active=True):
        """Centralized domain construction for thread lookup"""
        domain = [
            ("res_model", "=", model),
            ("res_id", "=", record_id),
        ]
        if user_id:
            domain.append(("user_id", "=", user_id))
        if active:
            domain.append(("active", "=", True))
        return domain

    @api.model
    def get_user_thread(self, model, record_id):
        """Get current user's thread for a record"""
        return self.search(
            self._get_thread_domain(self.env.user.id, model, record_id), limit=1
        )

    def get_thread_messages(self, trigger_message=None):
        """Get formatted messages for AI context"""
        self.ensure_one()
        messages = []

        domain = [
            ("model", "=", self.res_model),
            ("res_id", "=", self.res_id),
            (
                "subtype_id",
                "in",
                [
                    self.env.ref("llm_thread.mt_llm_question").id,
                    self.env.ref("llm_thread.mt_llm_answer").id,
                ],
            ),
        ]
        if trigger_message:
            domain.append(("id", "<=", trigger_message.id))

        messages.extend(
            message.to_llm_format()
            for message in self.env["mail.message"].search(
                domain, limit=10, order="id DESC"
            )
        )

        return list(reversed(messages))  # Return in chronological order

    def generate_response(self, trigger_message):
        """Generate AI response"""
        self.ensure_one()
        try:
            messages = self.get_thread_messages(trigger_message)
            return self.model_id.chat(messages)
        except Exception as e:
            _logger.exception("Failed to generate AI response")
            return {"error": str(e)}

    def action_view_record(self):
        """Navigate to the referenced record"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": self.res_model,
            "res_id": self.res_id,
            "views": [(False, "form")],
            "view_mode": "form",
            "target": "current",
        }
