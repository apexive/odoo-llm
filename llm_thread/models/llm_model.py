from odoo import models


class LLMModel(models.Model):
    _inherit = "llm.model"

    def action_start_chat(self):
        """Create a new thread for this model and open chat dialog"""
        self.ensure_one()

        # Create new thread
        thread = self.env["llm.thread"].create(
            {
                "name": f"Chat with {self.name}",
                "provider_id": self.provider_id.id,
                "model_id": self.id,
                "user_id": self.env.user.id,
            }
        )

        # Return chat dialog action
        return {
            "type": "ir.actions.client",
            "tag": "llm_chat_dialog",
            "name": f"Chat: {thread.name}",
            "params": {
                "thread_id": thread.id,
            },
            "target": "new",
        }
