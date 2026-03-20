import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class LLMSkill(models.Model):
    """
    One record per skill directory (skills/{name}/SKILL.md).

    The loader extracts `name` and `description` from the SKILL.md frontmatter
    and `content` from the body. Only `description` is embedded — one
    llm.knowledge.chunk per skill, stored in pgvector for similarity search.

    The LLM calls odoo_skill_searcher to get the short manifest (name +
    description) and odoo_skill_reader to load the full content on demand.
    """

    _name = "llm.skill"
    _description = "LLM Skill"
    _inherit = ["mail.thread"]
    _order = "name"

    name = fields.Char(
        string="Name",
        required=True,
        index=True,
        tracking=True,
        help="Skill identifier from SKILL.md frontmatter 'name:' field. kebab-case.",
    )

    description = fields.Text(
        string="Description",
        required=True,
        tracking=True,
        help=(
            "From SKILL.md frontmatter 'description:' field. "
            "This is the text that gets embedded for similarity search. "
            "Authors tune retrieval quality by improving this field."
        ),
    )

    content = fields.Text(
        string="Content",
        help="Full SKILL.md body (below the frontmatter). Loaded on demand by odoo_skill_reader.",
    )

    source_path = fields.Char(
        string="Source Directory",
        readonly=True,
        help="Absolute path to the skill directory on disk (e.g. /opt/odoo/addons/llm_skills/skills/my-skill).",
    )

    content_hash = fields.Char(
        string="Content Hash",
        readonly=True,
        help="SHA-256 of SKILL.md content. Used by the loader to skip unchanged files.",
    )

    active = fields.Boolean(default=True)

    loader_id = fields.Many2one(
        "llm.skills.loader",
        string="Loader",
        ondelete="cascade",
        readonly=True,
        help="The loader that manages this skill.",
    )
