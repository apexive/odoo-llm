from odoo import fields, models


class LLMAssistant(models.Model):
    """
    Extends llm.assistant with a skills collection reference.

    Multiple assistants can share the same collection or each use their own
    (e.g. a GAINDE assistant with a SYSCOHADA-focused collection).
    """

    _inherit = "llm.assistant"

    skills_collection_id = fields.Many2one(
        "llm.knowledge.collection",
        string="Skills Collection",
        ondelete="set null",
        tracking=True,
        help=(
            "Knowledge collection of Odoo skill descriptions. "
            "When configured, odoo_skill_searcher will use this collection. "
            "Leave empty to use the default 'Odoo Technical Skills' collection."
        ),
    )
