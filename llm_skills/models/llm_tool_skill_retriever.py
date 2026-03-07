import logging
from typing import Any

from odoo import api, models

_logger = logging.getLogger(__name__)


class LLMToolSkillRetriever(models.Model):
    """
    Provides the technical_skill_retriever @llm_tool.

    Inherits llm.tool to register a new implementation using the same
    pattern as llm_tool_knowledge_retriever. The tool resolves the
    collection to search from the assistant configuration at call time,
    so no collection_id argument is exposed to the LLM — the assistant
    configuration determines scope automatically.
    """

    _inherit = "llm.tool"

    @api.model
    def _get_available_implementations(self):
        implementations = super()._get_available_implementations()
        return implementations + [
            ("technical_skill_retriever", "Technical Skill Retriever")
        ]

    def technical_skill_retriever_execute(
        self,
        query: str,
        top_k: int = 3,
        similarity_cutoff: float = 0.35,
    ) -> dict[str, Any]:
        """
        Look up proven Odoo technical patterns before performing data operations.

        Call this tool when you:
        - Are about to query, create, update, or delete Odoo records but are
          unsure which model, domain, or field combination to use
        - Need to understand how two Odoo models relate to each other
        - Want the correct domain syntax for a filtering requirement
        - Need to know which fields to fetch for a given business concept

        Describe what you need to accomplish. Returns relevant skill documents
        with model names, domain examples, and field guidance extracted from
        previously solved problems.

        Do NOT call this tool for general Python or non-Odoo questions.

        Parameters:
            query: What you need to accomplish in Odoo. Be specific about the
                   business concept, e.g. "find customers with overdue invoices"
                   rather than just "get records".
            top_k: Maximum number of skill fragments to return (default 3).
            similarity_cutoff: Minimum semantic similarity threshold (default 0.35).
                               Lower values return more results; raise to 0.5+ for
                               stricter matching.
        """
        collection = self._resolve_technical_collection()
        if not collection:
            return {
                "query": query,
                "skills": [],
                "message": (
                    "No technical skills collection is configured on this assistant. "
                    "Proceeding with general knowledge."
                ),
            }

        search_limit = top_k * top_k * 2  # over-fetch, then re-rank
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
            "skills": results,
            "total": len(results),
        }

    def _resolve_technical_collection(self):
        """
        Walk context → message → llm.thread → llm.assistant →
        technical_skills_collection_id.

        Returns the collection record, or False if any step is missing.
        Intentionally silent — missing configuration is not an error,
        the tool just returns an empty result.
        """
        msg_id = self.env.context.get("message_id")
        if not msg_id:
            return False

        # The message context key varies; try both common forms
        msg = self.env["mail.message"].browse(msg_id)
        if not msg.exists():
            return False

        thread = self.env["llm.thread"].search(
            [("mail_thread_id", "=", msg.res_id),
             ("model", "=", msg.model)],
            limit=1,
        )
        if not thread:
            # Fallback: try direct res_id as thread id
            thread = self.env["llm.thread"].browse(msg.res_id)
            if not thread.exists():
                return False

        assistant = thread.assistant_id
        if not assistant:
            return False

        return assistant.technical_skills_collection_id or False
