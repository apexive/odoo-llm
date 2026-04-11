import hashlib
import logging
from pathlib import Path

import yaml

from odoo import _, api, fields, models
from odoo.tools import config

_logger = logging.getLogger(__name__)


class LLMSkillsLoader(models.Model):
    """
    Maps a filesystem directory of skill subdirectories to an llm.knowledge.collection.

    Each subdirectory must contain a SKILL.md file with YAML frontmatter:
        ---
        name: skill-name
        description: >
          Use when...
        ---
        # Full instructions...

    On every Odoo boot/upgrade, loaders with auto_sync_on_boot=True are triggered
    via _register_hook(). Each loader scans its skills_path for SKILL.md files,
    compares content hashes, and only re-embeds changed skills. Skills whose
    directories no longer exist on disk are deactivated.

    Embedding strategy:
    - One llm.knowledge.chunk per skill, content = description text
    - One llm.resource per skill (minimal holder, no pipeline processing)
    - Embedding via collection.embed_resources(specific_resource_ids=[...])

    The public interface is action_sync() — called by the UI button and _register_hook().
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
        help="Knowledge collection where skill descriptions will be embedded.",
    )

    skills_path = fields.Char(
        string="Skills Directory Path",
        required=True,
        tracking=True,
        help=(
            "Path to the directory containing skill subdirectories. "
            "Each subdirectory must have a SKILL.md file.\n"
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
        help="Number of active skills currently managed by this loader.",
    )

    def _compute_skill_count(self):
        for loader in self:
            loader.skill_count = self.env["llm.skill"].search_count([
                ("loader_id", "=", loader.id),
                ("active", "=", True),
            ])

    # -------------------------------------------------------------------------
    # Public interface
    # -------------------------------------------------------------------------

    def action_open_skills(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Skills",
            "res_model": "llm.skill",
            "view_mode": "list,form",
            "domain": [("loader_id", "=", self.id)],
            "context": {"default_loader_id": self.id},
        }

    def action_sync(self):
        """Public sync trigger. Called by UI button and _register_hook."""
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
        2. Scan subdirectories for SKILL.md files
        3. Upsert llm.skill + chunk + embedding for changed skills
        4. Deactivate skills whose directories no longer exist
        5. Update last_sync timestamp
        """
        self.ensure_one()

        resolved = self._resolve_skills_path()
        if not resolved:
            _logger.error(
                "llm_skills [%s]: skills_path '%s' could not be resolved.",
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

        try:
            self.collection_id.create_vector_collection()
        except Exception:
            pass  # May already exist

        found_names = set()
        synced = 0
        skipped = 0

        for skill_dir in sorted(resolved.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            name, changed = self._sync_skill_dir(skill_dir, skill_md)
            if name:
                found_names.add(name)
                if changed:
                    synced += 1
                else:
                    skipped += 1

        self._deactivate_removed_skills(found_names)
        self.last_sync = fields.Datetime.now()

        _logger.info(
            "llm_skills [%s]: done — %d synced, %d unchanged",
            self.name,
            synced,
            skipped,
        )

    def _sync_skill_dir(self, skill_dir: Path, skill_md: Path):
        """
        Sync a single skill directory.

        Returns:
            (name: str, changed: bool)
            name is None if the file could not be processed.
        """
        self.ensure_one()

        try:
            raw_content = skill_md.read_text(encoding="utf-8")
        except Exception as e:
            _logger.error(
                "llm_skills [%s]: cannot read '%s': %s", self.name, skill_md, e
            )
            return None, False

        content_hash = hashlib.sha256(raw_content.encode()).hexdigest()
        frontmatter, body = self._parse_frontmatter(raw_content)

        name = frontmatter.get("name") or skill_dir.name
        description = frontmatter.get("description") or ""
        if isinstance(description, str):
            description = description.strip()

        if not description:
            _logger.warning(
                "llm_skills [%s]: skill '%s' has no description — skipping embedding.",
                self.name,
                name,
            )

        Skill = self.env["llm.skill"]
        skill = Skill.search([
            ("name", "=", name),
            ("loader_id", "=", self.id),
        ], limit=1)

        if skill:
            if skill.content_hash == content_hash and self._skill_has_chunk(skill):
                return name, False
            skill.write({
                "description": description,
                "content": body,
                "source_path": str(skill_dir),
                "content_hash": content_hash,
                "active": True,
            })
            if description:
                self._upsert_skill_chunk(skill)
            _logger.info("llm_skills [%s]: updated skill '%s'", self.name, name)
        else:
            skill = Skill.create({
                "name": name,
                "description": description,
                "content": body,
                "source_path": str(skill_dir),
                "content_hash": content_hash,
                "loader_id": self.id,
            })
            if description:
                self._upsert_skill_chunk(skill)
            _logger.info("llm_skills [%s]: created skill '%s'", self.name, name)

        return name, True

    def _upsert_skill_chunk(self, skill):
        """
        Ensure exactly one llm.knowledge.chunk exists for this skill with
        content = skill.description, then embed it via the collection.

        Flow:
        1. Find or create a minimal llm.resource pointing to the skill
        2. Delete existing chunks (to force re-embedding on update)
        3. Create one chunk with content = description
        4. Call collection.embed_resources to generate and store the vector
        """
        resource = self._get_or_create_resource(skill)

        # Delete existing chunks so we re-embed fresh on update
        existing_chunks = self.env["llm.knowledge.chunk"].search([
            ("resource_id", "=", resource.id),
        ])
        if existing_chunks:
            existing_chunks.unlink()

        self.env["llm.knowledge.chunk"].create({
            "resource_id": resource.id,
            "content": skill.description,
            "sequence": 1,
            "metadata": {"skill_name": skill.name},
        })

        try:
            self.collection_id.embed_resources(
                specific_resource_ids=[resource.id]
            )
        except Exception as e:
            _logger.error(
                "llm_skills [%s]: embedding failed for skill '%s': %s",
                self.name,
                skill.name,
                e,
            )

    def _get_or_create_resource(self, skill):
        """
        Find or create a minimal llm.resource pointing to the given llm.skill.

        The resource is a holder that satisfies llm.knowledge.chunk.resource_id
        FK constraint. It is not processed through the pipeline — state stays
        'ready' and chunking is done manually by _upsert_skill_chunk.
        """
        SkillModel = self.env["ir.model"].search(
            [("model", "=", "llm.skill")], limit=1
        )
        if not SkillModel:
            _logger.error(
                "llm_skills [%s]: ir.model for 'llm.skill' not found.", self.name
            )
            return None

        resource = self.env["llm.resource"].search([
            ("model_id", "=", SkillModel.id),
            ("res_id", "=", skill.id),
        ], limit=1)

        if not resource:
            resource = self.env["llm.resource"].create({
                "name": skill.name,
                "model_id": SkillModel.id,
                "res_id": skill.id,
                "state": "ready",
                "collection_ids": [(4, self.collection_id.id)],
            })
        elif self.collection_id.id not in resource.collection_ids.ids:
            resource.collection_ids = [(4, self.collection_id.id)]

        return resource

    def _skill_has_chunk(self, skill) -> bool:
        """Return True if a chunk already exists for this skill in the collection."""
        SkillModel = self.env["ir.model"].search(
            [("model", "=", "llm.skill")], limit=1
        )
        if not SkillModel:
            return False
        resource = self.env["llm.resource"].search([
            ("model_id", "=", SkillModel.id),
            ("res_id", "=", skill.id),
        ], limit=1)
        if not resource:
            return False
        return bool(self.env["llm.knowledge.chunk"].search(
            [("resource_id", "=", resource.id)], limit=1
        ))

    def _deactivate_removed_skills(self, found_names: set):
        """
        Archive skills whose directories no longer exist on disk.
        Deletes the corresponding chunk (and pgvector embedding) via unlink().
        """
        stale = self.env["llm.skill"].search([
            ("loader_id", "=", self.id),
            ("name", "not in", list(found_names)),
            ("active", "=", True),
        ])
        for skill in stale:
            _logger.info(
                "llm_skills [%s]: deactivating removed skill '%s'",
                self.name,
                skill.name,
            )
            SkillModel = self.env["ir.model"].search(
                [("model", "=", "llm.skill")], limit=1
            )
            if SkillModel:
                resource = self.env["llm.resource"].search([
                    ("model_id", "=", SkillModel.id),
                    ("res_id", "=", skill.id),
                ], limit=1)
                if resource:
                    # Unlink cascades to chunks, which cleans up embeddings
                    resource.unlink()
            skill.write({"active": False})

    # -------------------------------------------------------------------------
    # Path resolution
    # -------------------------------------------------------------------------

    def _resolve_skills_path(self) -> Path | None:
        """
        Resolve self.skills_path to an absolute Path.
        Supports absolute paths or paths relative to any configured addons dir.
        Returns None if the path cannot be resolved to an existing directory.
        """
        p = Path(self.skills_path)
        if p.is_absolute():
            return p if p.is_dir() else None

        for addons_dir in [d.strip() for d in config.get("addons_path", "").split(",") if d.strip()]:
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
        Parse YAML frontmatter from SKILL.md content.

        Returns:
            (frontmatter_dict, body_str)
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
        Auto-discovers skills/ directories and triggers sync for all loaders.

        Uses a transaction-scoped advisory lock so only one worker process runs
        the boot sync. Other workers skip silently — they share the same DB state
        so the single sync covers everyone.
        """
        super()._register_hook()
        self._auto_discover_skill_loaders()

        # Only one worker should run the boot sync. Without this, concurrent
        # workers race to UPDATE the same llm_skills_loader rows, causing a
        # PostgreSQL serialization error that aborts the transaction and fails
        # registry loading.
        self.env.cr.execute("SELECT pg_try_advisory_xact_lock(853271649)")
        if not self.env.cr.fetchone()[0]:
            _logger.debug("llm_skills: boot sync skipped (another worker holds the lock)")
            return

        loaders = self.search([("auto_sync_on_boot", "=", True)])
        for loader in loaders:
            try:
                with self.env.cr.savepoint():
                    loader._sync_skills()
            except Exception:
                _logger.exception(
                    "llm_skills: failed to sync loader '%s' on boot", loader.name
                )

    @api.model
    def _auto_discover_skill_loaders(self):
        """
        Scan all installed addon directories for a skills/ subdirectory.
        Auto-create llm.skills.loader records for newly found paths.
        All auto-discovered loaders use the default 'Odoo Technical Skills' collection.
        """
        collection = self.env.ref(
            "llm_skills.llm_collection_meta_skills", raise_if_not_found=False
        )
        if not collection:
            _logger.info(
                "llm_skills: default collection not yet created — "
                "skipping auto-discovery. Will retry on next boot/upgrade."
            )
            return

        existing_paths = set(self.search([]).mapped("skills_path"))

        addon_paths = [p.strip() for p in config.get("addons_path", "").split(",") if p.strip()]
        for addons_dir in addon_paths:
            addons_dir = Path(addons_dir)
            if not addons_dir.is_dir():
                continue
            for module_dir in sorted(addons_dir.iterdir()):
                if not module_dir.is_dir():
                    continue
                skills_dir = module_dir / "skills"
                if not skills_dir.is_dir():
                    continue
                module_name = module_dir.name
                installed = self.env["ir.module.module"].search(
                    [("name", "=", module_name), ("state", "=", "installed")],
                    limit=1,
                )
                if not installed:
                    continue
                skills_path = str(skills_dir)
                if skills_path in existing_paths:
                    continue
                loader = self.create({
                    "name": f"{module_name} Skills",
                    "collection_id": collection.id,
                    "skills_path": skills_path,
                    "auto_sync_on_boot": True,
                })
                existing_paths.add(skills_path)
                _logger.info(
                    "llm_skills: auto-discovered skills/ in '%s' → loader '%s' (id=%s)",
                    module_name,
                    loader.name,
                    loader.id,
                )
