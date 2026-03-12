from odoo import fields, models


class LLMAssistant(models.Model):
    """
    Extends llm.assistant with a technical skills collection reference.

    The technical_skill_retriever tool resolves its collection at runtime
    by walking: context message → llm.thread → llm.assistant →
    technical_skills_collection_id.

    Multiple assistants can share the same collection (e.g. a shared
    "Odoo Patterns" collection) or each use their own (e.g. GAINDE assistant
    uses a SYSCOHADA-focused collection).
    """

    _inherit = "llm.assistant"

    technical_skills_collection_id = fields.Many2one(
        "llm.knowledge.collection",
        string="Technical Skills Collection",
        ondelete="set null",
        tracking=True,
        help=(
            "Knowledge collection of proven Odoo technical patterns. "
            "When configured, the technical_skill_retriever tool will search "
            "this collection to guide the LLM on which models, domains, and "
            "fields to use before performing data operations."
        ),
    )
