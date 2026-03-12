import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class LLMSkillDocument(models.Model):
    """
    Stores the raw markdown content of a skill document loaded from the filesystem.

    Each record corresponds to one .md file in a skills directory. The loader
    creates/updates these records and llm.resource points to them for the RAG
    pipeline (retrieve → parse → chunk → embed).

    Content is parsed via llm_get_fields() which returns the markdown text
    directly — no URL retrieval needed.
    """

    _name = "llm.skill.document"
    _description = "LLM Skill Document"
    _inherit = ["mail.thread"]
    _order = "skill_id"

    name = fields.Char(
        string="Title",
        required=True,
        tracking=True,
    )

    skill_id = fields.Char(
        string="Skill ID",
        required=True,
        index=True,
        tracking=True,
        help=(
            "Stable unique identifier from the skill file frontmatter 'id:' field. "
            "Falls back to the filename stem if not present. "
            "Used to track identity across content changes."
        ),
    )

    content = fields.Text(
        string="Markdown Content",
        required=True,
        help="Full markdown content of the skill document including YAML frontmatter.",
    )

    content_hash = fields.Char(
        string="Content Hash",
        readonly=True,
        help="SHA-256 hash of the content field. Used by the loader to skip unchanged files.",
    )

    tags = fields.Char(
        string="Tags",
        help="Comma-separated tags extracted from frontmatter. Used for filtering.",
    )

    odoo_models = fields.Char(
        string="Odoo Models",
        help="Comma-separated Odoo model names referenced in this skill.",
    )

    loader_id = fields.Many2one(
        "llm.skills.loader",
        string="Loader",
        ondelete="cascade",
        readonly=True,
        help="The loader that created this skill document record.",
    )

    active = fields.Boolean(default=True)

    # -------------------------------------------------------------------------
    # RAG pipeline integration
    # -------------------------------------------------------------------------

    def llm_get_retrieval_details(self):
        """
        Called by llm.resource retriever. Signals that content is already
        available in-memory — no URL or binary fetch needed.
        Returning None causes the retriever to call retrieve_default(),
        which just marks the resource as 'retrieved' so parsing can proceed.
        """
        self.ensure_one()
        return None

    def llm_get_fields(self, _resource):
        """
        Called by llm.resource parser. Returns the skill markdown content
        directly so it gets stored in llm.resource.content and chunked/embedded.

        The full frontmatter is included intentionally — it carries tags,
        model names, and title which enrich semantic search recall.
        """
        self.ensure_one()
        return [
            {
                "field_name": "content",
                "mimetype": "text/markdown",
                "rawcontent": self.content or "",
            }
        ]
