from odoo import fields, models

# Skills are atomic knowledge units — keep each one as a single chunk.
# 2000 tokens comfortably fits any well-authored skill (typically 300–600 tokens)
# while acting as a safety valve for accidental oversized skills.
_SKILL_CHUNK_SIZE = 2000
_SKILL_CHUNK_OVERLAP = 0


class LLMResource(models.Model):
    """
    Extends llm.resource with skill-specific tracking fields.
    These fields are set by llm.skills.loader and used for:
    - Identity tracking: skill_external_id links a resource to a skill file
    - Change detection: skill_content_hash avoids re-embedding unchanged files

    Chunking override:
    Skill documents are atomic — a skill is one coherent unit of knowledge
    and must never be split across chunks. We override create() to force
    target_chunk_size=8000 and target_chunk_overlap=0 on any resource that
    references an llm.skill.document, regardless of the collection's defaults.
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

    def _is_skill_resource(self):
        """Return True if this resource points to an llm.skill.document record."""
        self.ensure_one()
        return self.res_model == "llm.skill.document"

    @staticmethod
    def _skill_chunk_overrides():
        return {
            "target_chunk_size": _SKILL_CHUNK_SIZE,
            "target_chunk_overlap": _SKILL_CHUNK_OVERLAP,
        }

    def create(self, vals_list):
        resources = super().create(vals_list)
        skill_model = self.env["ir.model"].search(
            [("model", "=", "llm.skill.document")], limit=1
        )
        if skill_model:
            skill_resources = resources.filtered(
                lambda r: r.model_id.id == skill_model.id
            )
            if skill_resources:
                skill_resources.write(self._skill_chunk_overrides())
        return resources
