import logging
from typing import Any

from odoo import api, models

_logger = logging.getLogger(__name__)


class LLMToolSkillRetriever(models.Model):
    """
    Provides the technical_skill_retriever tool.

    Mirrors the knowledge_retriever pattern: collection_id is an explicit
    required parameter, and available skills collections are dynamically
    injected into the schema description at runtime. No assistant context
    resolution needed — works identically in direct MCP sessions,
    WhatsApp conversations, or any other context.
    """

    _inherit = "llm.tool"

    @api.model
    def _get_available_implementations(self):
        implementations = super()._get_available_implementations()
        return implementations + [
            ("technical_skill_retriever", "Technical Skill Retriever")
        ]

    @api.model
    def _get_available_skills_collections(self):
        """Return only collections that back a skills loader."""
        loaders = self.env["llm.skills.loader"].sudo().search([])
        seen = {}
        for loader in loaders:
            coll = loader.collection_id
            if coll and coll.id not in seen:
                seen[coll.id] = coll.name
        return [(str(coll_id), name) for coll_id, name in seen.items()]

    def get_input_schema(self):
        schema = super().get_input_schema()
        if self.implementation == "technical_skill_retriever":
            collections = self._get_available_skills_collections()
            desc = ", ".join(f"'{name}' (ID: {coll_id})" for coll_id, name in collections)
            if "properties" in schema and "collection_id" in schema["properties"]:
                schema["properties"]["collection_id"]["description"] = (
                    f"ID of the skills collection to search. Available: {desc}"
                )
        return schema

    def technical_skill_retriever_execute(
        self,
        query: str,
        collection_id: int,
        top_k: int = 3,
        similarity_cutoff: float = 0.35,
    ) -> dict[str, Any]:
        """
        Look up proven Odoo technical patterns before performing data operations.

        Call this tool BEFORE querying, creating, updating, or deleting Odoo
        records when you are unsure which model, domain, fields, or method to
        use. Describe what you need to accomplish — returns relevant skill
        documents with model names, domain examples, and field guidance
        extracted from previously solved problems.

        Do NOT call this tool for general Python or non-Odoo questions.

        Parameters:
            query: What you need to accomplish in Odoo. Be specific, e.g.
                   "find customers with overdue invoices" not just "get records".
            collection_id: REQUIRED. ID of the skills collection to search.
            top_k: Maximum number of skill fragments to return (default 3).
            similarity_cutoff: Minimum semantic similarity threshold (default
                               0.35). Lower values return more results.
        """
        _logger.info(
            "technical_skill_retriever_execute: query=%s collection_id=%s",
            query, collection_id,
        )

        if not collection_id:
            return {
                "query": query,
                "skills": [],
                "message": "collection_id is required. Check the tool schema for available collections.",
            }

        collection = self.env["llm.knowledge.collection"].browse(collection_id)
        if not collection.exists():
            return {
                "query": query,
                "skills": [],
                "message": f"Collection ID {collection_id} not found.",
            }

        search_limit = top_k * top_k * 2
        try:
            chunks = self.env["llm.knowledge.chunk"].search(
                args=[("embedding", "=", query)],
                limit=search_limit,
                collection_id=collection.id,
                query_min_similarity=similarity_cutoff,
            )
        except Exception as e:
            _logger.error(
                "technical_skill_retriever: chunk search failed: %s", e, exc_info=True
            )
            return {"query": query, "skills": [], "error": str(e)}

        if not chunks:
            return {
                "query": query,
                "collection": collection.name,
                "skills": [],
                "message": "No relevant skills found for this query.",
            }

        results = self._process_search_results(
            chunks=chunks,
            top_k=top_k,
            top_n=top_k,
        )

        return {
            "query": query,
            "collection": collection.name,
            "collection_id": collection.id,
            "skills": results,
            "total": len(results),
        }
