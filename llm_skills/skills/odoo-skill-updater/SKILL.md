---
name: odoo-skill-updater
description: >
  Use when an existing skill needs correction, improvement, or its description
  needs tuning for better retrieval. Trigger when the user says: update a
  skill, fix a skill, improve this skill, the skill is wrong, the skill
  description is not matching, skill not being found, skill triggering too
  often, or wants to change skill content. Also trigger when you notice a
  skill has outdated information after an Odoo upgrade.
---

# Update an Existing Odoo Skill

## When to update

- The skill instructions are incorrect or outdated
- The skill is not being retrieved when it should be (description too narrow)
- The skill is being retrieved when it shouldn't (description too broad)
- An Odoo version upgrade changed the relevant APIs or field names
- The skill body has incomplete or missing steps

## How to update

1. **Confirm the skill exists** — use `odoo_skill_reader("skill-name")` to read
   the current content and confirm you have the right skill.

2. **Find the file on disk** — locate the loader via **LLM → Skills → Loaders**,
   open it, note the `Skills Directory Path`. The file is at:
   `{skills_path}/{skill-name}/SKILL.md`

3. **Edit SKILL.md** — update the frontmatter `description:` and/or the body.

4. **Trigger sync** — the loader detects the content hash change and re-embeds
   the description automatically. Go to:
   **LLM → Skills → Loaders** → "Sync Now"

5. **Verify** — call `odoo_skill_reader("skill-name")` again to confirm the
   content was updated, and `odoo_skill_searcher("...")` to confirm retrieval.

## Tuning the description

The `description` field is what gets embedded and searched. If a skill is not
being found for relevant queries, make the description more "pushy":

- Add synonyms: "also called X, Y, or Z"
- Add trigger phrases: "when the user mentions...", "use whenever..."
- Cover edge cases: "even if the user only partially describes the task"

If a skill is triggering for unrelated queries, narrow the description by
removing broad terms and being more specific about the domain.

## What NOT to change

- `name:` — this is the stable identifier. Changing it creates a new skill
  and orphans the old one. If a rename is truly needed, create a new skill
  with the correct name and delete the old one using `odoo-skill-deleter`.
