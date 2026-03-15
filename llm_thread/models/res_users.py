from odoo import models


class ResUsers(models.Model):
    _inherit = "res.users"

    def _init_messaging(self):
        """Extend init_messaging to include LLM threads following Odoo v17 patterns."""
        values = super()._init_messaging()

        # Load user's recent LLM threads
        llm_threads = self.env["llm.thread"].search(
            [("user_id", "=", self.id), ("active", "=", True)], order="write_date DESC"
        )

        if llm_threads:
            values["llmThreads"] = llm_threads._thread_to_store_info()

        return values
