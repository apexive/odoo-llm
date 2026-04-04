import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class LLMToolSkills(models.Model):
    """
    Provides odoo_skill_searcher and odoo_skill_reader tools.

    Two-stage progressive disclosure:
    1. odoo_skill_searcher — embeds query, returns top-4 manifest (name + description)
    2. odoo_skill_reader  — loads full SKILL.md body by name

    The collection is resolved from the first active skills loader, falling back
    to the default llm_collection_meta_skills ref.
    """

    _inherit = "llm.tool"

    @api.model
    def _get_available_implementations(self):
        return super()._get_available_implementations() + [
            ("odoo_skill_searcher", "Odoo Skill Searcher"),
            ("odoo_skill_reader", "Odoo Skill Reader"),
        ]

    @api.model
    def _get_skills_collection(self):
        """
        Resolve the skills collection to search.
        Prefers the default collection; falls back to any loader's collection.
        """
        collection = self.env.ref(
            "llm_skills.llm_collection_meta_skills", raise_if_not_found=False
        )
        if collection and collection.exists():
            return collection

        loader = self.env["llm.skills.loader"].search([], limit=1)
        return loader.collection_id if loader else None

    def odoo_skill_searcher_execute(self, query: str = "") -> list:
        """
        Search for available Odoo skills by describing what you need to accomplish.
        Returns a short manifest of the most relevant skills (name + description).
        Call this first when you need guidance on an unfamiliar task.
        Call with empty query to list all available skills.
        """
        _logger.info("odoo_skill_searcher: query=%r", query)

        if not query:
            skills = self.env["llm.skill"].search([("active", "=", True)])
            return [{"name": s.name, "description": s.description} for s in skills]

        collection = self._get_skills_collection()
        if not collection:
            return [{"error": "No skills collection configured. Run a skills loader sync first."}]

        try:
            chunks = self.env["llm.knowledge.chunk"].search(
                args=[("embedding", "=", query)],
                limit=4,
                collection_id=collection.id,
                query_min_similarity=0.3,
            )
        except Exception as e:
            _logger.error("odoo_skill_searcher: search failed: %s", e, exc_info=True)
            return [{"error": str(e)}]

        results = []
        seen_skills = set()
        for chunk in chunks:
            if chunk.resource_id.res_model != "llm.skill":
                continue
            skill_id = chunk.resource_id.res_id
            if skill_id in seen_skills:
                continue
            seen_skills.add(skill_id)
            skill = self.env["llm.skill"].browse(skill_id)
            if skill.exists() and skill.active:
                results.append({"name": skill.name, "description": skill.description})

        return results

    def odoo_skill_reader_execute(self, skill_name: str) -> str:
        """
        Load the full instructions of an Odoo skill by name.
        Call this after odoo_skill_searcher to get the complete guidance
        for a skill before executing it.
        """
        _logger.info("odoo_skill_reader: skill_name=%r", skill_name)

        skill = self.env["llm.skill"].search(
            [("name", "=", skill_name), ("active", "=", True)], limit=1
        )
        if not skill:
            return (
                f"Skill '{skill_name}' not found or inactive. "
                f"Use odoo_skill_searcher to find available skills."
            )

        return skill.content or f"Skill '{skill_name}' has no content body."
