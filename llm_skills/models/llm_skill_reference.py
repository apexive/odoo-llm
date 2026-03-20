from odoo import fields, models


class LLMSkillReference(models.Model):
    """
    Supporting reference files for a skill (e.g. references/account_move_fields.md).

    Stub model — loader sync for reference files is deferred until the first
    reference-heavy skill is actually needed. Current skills are self-contained.
    """

    _name = "llm.skill.reference"
    _description = "LLM Skill Reference File"
    _order = "skill_id, path"

    skill_id = fields.Many2one(
        "llm.skill",
        string="Skill",
        required=True,
        ondelete="cascade",
        index=True,
    )

    path = fields.Char(
        string="Relative Path",
        help="Relative path within the skill directory, e.g. 'references/account_move_fields.md'.",
    )

    content = fields.Text(
        string="Content",
        help="Raw text content of the reference file.",
    )

    checksum = fields.Char(
        string="Checksum",
        help="SHA-256 of the file content, for change detection in the loader.",
    )
