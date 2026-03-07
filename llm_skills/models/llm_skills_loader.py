import hashlib
import logging
from pathlib import Path

import yaml

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class LLMSkillsLoader(models.Model):
    """
    Maps a filesystem directory of skill .md files to an llm.knowledge.collection.

    On every Odoo boot/upgrade, all loaders with auto_sync_on_boot=True are
    triggered via _register_hook(). Each loader scans its skills_path recursively,
    compares file content hashes against stored values, and only re-processes
    files that have changed. Files removed from disk are deactivated.

    The public interface is action_sync() — this is the method called by:
    - The UI "Sync Now" button
    - _register_hook() on boot/upgrade
    - llm_skills_webhook (future) on git push events

    Skill file format (.md with YAML frontmatter):
        ---
        id: unique-stable-id
        title: Human readable title
        tags: [tag1, tag2]
        odoo_models: [res.partner, account.move]
        tools: [odoo_record_retriever]
        ---
        # Skill content in markdown...
    """

    _name = "llm.skills.loader"
    _description = "LLM Skills Loader"
    _inherit = ["mail.thread"]
    _order = "name"

    name = fields.Char(
        string="Name",
        required=True,
        tracking=True,
    )

    collection_id = fields.Many2one(
        "llm.knowledge.collection",
        string="Target Collection",
        required=True,
        ondelete="restrict",
        tracking=True,
        help="Knowledge collection where skill documents will be loaded.",
    )

    skills_path = fields.Char(
        string="Skills Directory Path",
        required=True,
        tracking=True,
        help=(
            "Path to the directory containing skill .md files. Scanned recursively.\n"
            "Accepts absolute paths or paths relative to any configured addons directory.\n"
            "Example (absolute): /opt/odoo/addons/my_module/skills\n"
            "Example (relative): my_module/skills"
        ),
    )

    auto_sync_on_boot = fields.Boolean(
        string="Auto Sync on Boot/Upgrade",
        default=True,
        tracking=True,
        help="Automatically sync skills on every Odoo start or module upgrade.",
    )

    last_sync = fields.Datetime(
        string="Last Sync",
        readonly=True,
        tracking=True,
    )

    skill_count = fields.Integer(
        string="Skills Loaded",
        compute="_compute_skill_count",
        help="Number of active skill resources currently in the target collection.",
    )

    @api.depends("collection_id")
    def _compute_skill_count(self):
        for loader in self:
            if loader.collection_id:
                loader.skill_count = self.env["llm.resource"].search_count([
                    ("collection_ids", "in", loader.collection_id.id),
                    ("skill_external_id", "!=", False),
                    ("active", "=", True),
                ])
            else:
                loader.skill_count = 0

    # -------------------------------------------------------------------------
    # Public interface
    # -------------------------------------------------------------------------

    def action_open_skill_documents(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Skill Documents",
            "res_model": "llm.skill.document",
            "view_mode": "list,form",
            "domain": [("loader_id", "=", self.id)],
            "context": {"default_loader_id": self.id},
        }

    def action_sync(self):
        """
        Public sync trigger. Called by UI button, _register_hook, and
        llm_skills_webhook. Syncs all selected loaders.
        """
        for loader in self:
            loader._sync_skills()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Skills Synced"),
                "message": _(
                    "Sync complete. %(count)d active skills in collection '%(name)s'.",
                    count=self[:1].skill_count,
                    name=self[:1].collection_id.name if self else "",
                ),
                "type": "success",
                "sticky": False,
            },
        }

    # -------------------------------------------------------------------------
    # Core sync logic
    # -------------------------------------------------------------------------

    def _sync_skills(self):
        """
        Full sync for this loader:
        1. Resolve and validate skills_path
        2. Scan all .md files recursively
        3. Create/update llm.skill.document + llm.resource for changed files
        4. Deactivate resources for files no longer on disk
        5. Update last_sync timestamp
        """
        self.ensure_one()

        resolved = self._resolve_skills_path()
        if not resolved:
            _logger.error(
                "llm_skills [%s]: skills_path '%s' could not be resolved or does not exist.",
                self.name,
                self.skills_path,
            )
            return

        _logger.info(
            "llm_skills [%s]: syncing from '%s' into collection '%s'",
            self.name,
            resolved,
            self.collection_id.name,
        )

        # Ensure the vector store collection exists before adding resources
        try:
            self.collection_id.create_vector_collection()
        except Exception:
            pass  # Collection may already exist — not an error

        found_skill_ids = set()
        synced = 0
        skipped = 0

        for md_file in sorted(resolved.rglob("*.md")):
            skill_id, changed = self._sync_skill_file(md_file)
            if skill_id:
                found_skill_ids.add(skill_id)
                if changed:
                    synced += 1
                else:
                    skipped += 1

        self._deactivate_removed_skills(found_skill_ids)
        self.last_sync = fields.Datetime.now()

        _logger.info(
            "llm_skills [%s]: done — %d synced, %d unchanged, collection '%s'",
            self.name,
            synced,
            skipped,
            self.collection_id.name,
        )

    def _sync_skill_file(self, md_file: Path):
        """
        Sync a single skill .md file.

        Steps:
        1. Read file and compute SHA-256 hash
        2. Parse YAML frontmatter for metadata
        3. Find or create the llm.skill.document record
        4. If content unchanged, skip (return changed=False)
        5. If new or changed, update skill document + reset resource for re-processing
        6. Create llm.resource pointing to the skill document if it doesn't exist

        Returns:
            (skill_id: str, changed: bool)
            skill_id is None if the file could not be processed.
        """
        self.ensure_one()

        try:
            raw_content = md_file.read_text(encoding="utf-8")
        except Exception as e:
            _logger.error(
                "llm_skills [%s]: cannot read file '%s': %s", self.name, md_file, e
            )
            return None, False

        content_hash = hashlib.sha256(raw_content.encode()).hexdigest()
        frontmatter, _body = self._parse_frontmatter(raw_content)

        skill_id = frontmatter.get("id") or md_file.stem
        title = frontmatter.get("title") or skill_id
        tags = ", ".join(frontmatter.get("tags") or [])
        odoo_models = ", ".join(frontmatter.get("odoo_models") or [])

        # Find existing skill document for this loader + skill_id
        SkillDoc = self.env["llm.skill.document"]
        skill_doc = SkillDoc.search([
            ("skill_id", "=", skill_id),
            ("loader_id", "=", self.id),
        ], limit=1)

        if skill_doc:
            if skill_doc.content_hash == content_hash:
                # Nothing changed — skip
                return skill_id, False
            # Content changed — update document, reset resource for re-processing
            skill_doc.write({
                "name": title,
                "content": raw_content,
                "content_hash": content_hash,
                "tags": tags,
                "odoo_models": odoo_models,
                "active": True,
            })
            # Reset the linked resource so it goes through the pipeline again
            resource = self._get_resource_for_skill(skill_doc)
            if resource:
                resource.write({
                    "name": title,
                    "state": "draft",
                    "skill_content_hash": content_hash,
                })
                resource.process_resource()
            _logger.info("llm_skills [%s]: updated skill '%s'", self.name, skill_id)
        else:
            # New skill — create document record first, then resource
            skill_doc = SkillDoc.create({
                "name": title,
                "skill_id": skill_id,
                "content": raw_content,
                "content_hash": content_hash,
                "tags": tags,
                "odoo_models": odoo_models,
                "loader_id": self.id,
            })
            self._create_resource_for_skill(skill_doc, title, content_hash)
            _logger.info("llm_skills [%s]: created skill '%s'", self.name, skill_id)

        return skill_id, True

    def _create_resource_for_skill(self, skill_doc, title: str, content_hash: str):
        """
        Create an llm.resource pointing to an llm.skill.document record.
        The resource uses (model_id, res_id) to reference the skill document,
        consistent with how all llm.resource records work.
        """
        SkillDocModel = self.env["ir.model"].search(
            [("model", "=", "llm.skill.document")], limit=1
        )
        if not SkillDocModel:
            _logger.error(
                "llm_skills [%s]: ir.model record for 'llm.skill.document' not found.",
                self.name,
            )
            return None

        resource = self.env["llm.resource"].create({
            "name": title,
            "model_id": SkillDocModel.id,
            "res_id": skill_doc.id,
            "skill_external_id": skill_doc.skill_id,
            "skill_content_hash": content_hash,
            "collection_ids": [(4, self.collection_id.id)],
        })
        resource.process_resource()
        return resource

    def _get_resource_for_skill(self, skill_doc):
        """Find the llm.resource that points to a given llm.skill.document record."""
        SkillDocModel = self.env["ir.model"].search(
            [("model", "=", "llm.skill.document")], limit=1
        )
        if not SkillDocModel:
            return None
        return self.env["llm.resource"].search([
            ("model_id", "=", SkillDocModel.id),
            ("res_id", "=", skill_doc.id),
        ], limit=1)

    def _deactivate_removed_skills(self, found_skill_ids: set):
        """
        Archive skill documents (and their resources) whose .md files
        no longer exist on disk. This keeps the collection consistent
        with the filesystem state.
        """
        stale_docs = self.env["llm.skill.document"].search([
            ("loader_id", "=", self.id),
            ("skill_id", "not in", list(found_skill_ids)),
            ("active", "=", True),
        ])
        for doc in stale_docs:
            _logger.info(
                "llm_skills [%s]: deactivating removed skill '%s'",
                self.name,
                doc.skill_id,
            )
            resource = self._get_resource_for_skill(doc)
            if resource:
                resource.write({"active": False})
            doc.write({"active": False})

    # -------------------------------------------------------------------------
    # Path resolution
    # -------------------------------------------------------------------------

    def _resolve_skills_path(self) -> Path | None:
        """
        Resolve self.skills_path to an absolute Path object.

        Supports:
        - Absolute paths: /opt/odoo/addons/my_module/skills
        - Addons-relative paths: my_module/skills
          (tried against each directory in the Odoo addons path)

        Returns None if the path cannot be resolved to an existing directory.
        """
        p = Path(self.skills_path)
        if p.is_absolute():
            return p if p.is_dir() else None

        # Try relative to each configured addons path
        for addons_dir in self.env["ir.module.module"]._get_modules_path():
            candidate = Path(addons_dir) / p
            if candidate.is_dir():
                return candidate

        return None

    # -------------------------------------------------------------------------
    # Frontmatter parsing
    # -------------------------------------------------------------------------

    @staticmethod
    def _parse_frontmatter(content: str) -> tuple:
        """
        Parse YAML frontmatter from markdown content.

        Expected format:
            ---
            id: skill-id
            title: Skill title
            tags: [tag1, tag2]
            ---
            # Markdown body...

        Returns:
            (frontmatter_dict, body_str)
            frontmatter_dict is empty dict if no valid frontmatter found.
        """
        if not content.startswith("---"):
            return {}, content

        try:
            end_idx = content.index("---", 3)
            fm_text = content[3:end_idx]
            fm = yaml.safe_load(fm_text) or {}
            body = content[end_idx + 3:].lstrip("\n")
            return fm, body
        except Exception as e:
            _logger.debug("llm_skills: frontmatter parse failed: %s", e)
            return {}, content

    # -------------------------------------------------------------------------
    # Boot hook
    # -------------------------------------------------------------------------

    @api.model
    def _register_hook(self):
        """
        Called by Odoo on every server start and module upgrade.
        Triggers sync for all loaders with auto_sync_on_boot=True.
        Failures on individual loaders are caught and logged — one broken
        loader does not block others or prevent Odoo from starting.
        """
        super()._register_hook()
        loaders = self.search([("auto_sync_on_boot", "=", True)])
        for loader in loaders:
            try:
                loader._sync_skills()
            except Exception:
                _logger.exception(
                    "llm_skills: failed to sync loader '%s' on boot", loader.name
                )
