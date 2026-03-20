---
name: odoo-skill-deleter
description: >
  Use when a skill is obsolete, duplicated, incorrect, or should be removed.
  Trigger when the user says: delete a skill, remove a skill, this skill is
  wrong and should not exist, archive a skill, clean up skills, or a skill is
  a duplicate of another. Also trigger when merging two overlapping skills
  into one.
---

# Delete an Odoo Skill

## When to delete vs archive

**Delete** (remove directory from disk):

- The skill is completely wrong and has no salvageable content
- The skill has been fully superseded by a better skill
- Exact duplicate of another skill (merge content first if needed)

**Archive** (keep files, deactivate record in UI):

- The skill may be needed again later
- Unsure if it's still relevant
- Archive via: **LLM → Skills → Skills** → open the record → toggle Active off

## How to delete permanently

1. **Confirm the right skill** — use `odoo_skill_reader("skill-name")` to read
   the content and make sure you're deleting the intended one.

2. **Remove the directory from disk:**

   ```
   rm -rf {skills_path}/{skill-name}/
   ```

3. **Trigger sync** — the loader detects the missing directory and deactivates
   the `llm.skill` record and its pgvector embedding:
   **LLM → Skills → Loaders** → "Sync Now"

The `llm.knowledge.chunk` and its embedding are automatically cleaned up.
The `llm.skill` record is archived (not hard-deleted) so history is preserved.

## Downstream effects

- Any assistant using `odoo_skill_searcher` will simply not find this skill anymore
- If the skill was in active use, consider adding a note to the superseding skill
  explaining the transition
- Skill archives are visible via **LLM → Skills → Skills** with the Archived filter

## Finding duplicate skills

```
odoo_skill_searcher("description of what the skill does")
```

Review the top results. If two skills cover the same pattern, merge the better
content into one SKILL.md and delete the other directory.
