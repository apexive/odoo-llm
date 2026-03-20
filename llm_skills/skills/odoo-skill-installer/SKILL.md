---
name: odoo-skill-installer
description: >
  Use when the user wants to install a skill from an external source, a URL,
  a Git repository, or the community skills marketplace. Trigger when the user
  says: install a skill, download a skill, add a community skill, get skills
  from GitHub, import a skill, or references moctarjallo/skills or any external
  skill source. Also trigger when setting up skills from a new addon.
---

# Install a Community Odoo Skill

## Sources

Skills can be installed from:

- A URL pointing to a raw SKILL.md file
- A GitHub/GitLab repository containing a `skills/` directory
- The community marketplace: `github.com/moctarjallo/skills`
- Another installed Odoo addon that ships a `skills/` directory

## Installation steps

### From a URL (single skill)

1. Download the SKILL.md file (use `curl` or copy the raw content)
2. Create the skill directory in the target addon:
   ```
   mkdir -p {skills_path}/{skill-name}/
   ```
3. Save the content as `SKILL.md` in that directory
4. Trigger sync: **LLM → Skills → Loaders** → "Sync Now"

### From a Git repository

1. Clone or download the repository
2. Copy the relevant skill directories into the target addon's `skills/` folder:
   ```
   cp -r path/to/repo/skills/skill-name/ {skills_path}/
   ```
3. Trigger sync

### From a new addon with skills/

If an addon ships its own `skills/` directory, the loader auto-discovers it on
the next Odoo start (no manual action needed) — as long as the addon is installed.

## Validation before installing

Before installing a community skill:

1. Read the SKILL.md and verify the `name:` is unique:
   `odoo_skill_searcher("what the skill does")`
2. Check the `description:` is trigger-appropriate for your use case
3. Review the body content for correctness against your Odoo version

## After installation

The loader syncs automatically on Odoo restart, or immediately via
**LLM → Skills → Loaders** → "Sync Now".

Verify the skill was loaded: **LLM → Skills → Skills** → search for the skill name.
Verify it's searchable: `odoo_skill_searcher("what the skill does")`.
