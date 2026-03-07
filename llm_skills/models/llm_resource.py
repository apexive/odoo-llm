from odoo import fields, models


class LLMResource(models.Model):
    """
    Extends llm.resource with skill-specific tracking fields.
    These fields are set by llm.skills.loader and used for:
    - Identity tracking: skill_external_id links a resource to a skill file
    - Change detection: skill_content_hash avoids re-embedding unchanged files
    """

    _inherit = "llm.resource"

    skill_external_id = fields.Char(
        string="Skill ID",
        index=True,
        help=(
            "Stable identifier from the skill document's 'skill_id' field. "
            "Set by the skills loader. Used to locate the resource on subsequent "
            "syncs without relying on name or record ID."
        ),
    )

    skill_content_hash = fields.Char(
        string="Skill Content Hash",
        help=(
            "SHA-256 hash of the skill document content at last sync. "
            "If the hash matches the current file, the resource is skipped "
            "during sync to avoid unnecessary re-embedding."
        ),
    )
