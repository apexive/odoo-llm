from odoo import models


class ResUsers(models.Model):
    _inherit = "res.users"

    def _init_messaging(self):
        """Extend init_messaging to include LLM threads following Odoo 17 patterns."""
        # Get base messaging data from parent
        values = super()._init_messaging()

        # Load user's recent LLM threads (similar to how discuss.channel works)
        llm_threads = self.env["llm.thread"].search(
            [("user_id", "=", self.id), ("active", "=", True)],
            order="write_date DESC",
            limit=100  # Limit to avoid loading too many threads
        )

        # Add LLM threads to the returned values
        # In Odoo 17, we add threads directly to the values dict
        if llm_threads:
            values['llm_threads'] = llm_threads.mail_thread_format()

        return values
