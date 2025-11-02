from odoo import models


class ResUsers(models.Model):
    _inherit = "res.users"

    def _init_messaging(self, store):
        """Extend init_messaging to include LLM threads following Odoo patterns."""
        super()._init_messaging(store)

        # Load user's recent LLM threads (similar to how discuss.channel works)
        llm_threads = self.env["llm.thread"].search(
            [("user_id", "=", self.id), ("active", "=", True)], order="write_date DESC"
        )

        # Use inherited _thread_to_store method from mail.thread
        if llm_threads:
            llm_threads._thread_to_store(store)
