---
id: skill-authoring-guide
title: How to Write a Skill File
tags: [skills, authoring, meta]
odoo_models: []
tools: []
---

# How to Write a Skill File

## When to use
Use this skill whenever you need to create or update a skill `.md` file in a project module's `skills/` directory (e.g. `whatsapp_llm/skills/`, `account_budget_gainde/skills/`).

## Skill file format

A skill file is a Markdown file with a YAML frontmatter block at the top:

```
---
id: unique-stable-id
title: Human readable title
tags: [tag1, tag2]
odoo_models: [res.partner, account.move]
tools: [odoo_record_retriever]
---

# Title

## When to use
Describe the exact business question or situation this skill addresses.

## Solution
Step-by-step approach: which Odoo models to query, which fields matter, filters to apply.

## Variants
Edge cases or alternative approaches for related situations.

## Notes
Gotchas, performance considerations, or important constraints.
```

## Frontmatter fields

- **`id`** — stable snake-case or kebab-case identifier. Never change this after creation — it is used to track the skill across content edits. Use the filename stem as the id.
- **`title`** — human-readable name shown in the Odoo UI.
- **`tags`** — list of lowercase keywords for filtering. Use domain tags like `invoicing`, `whatsapp`, `partners`, `budget`.
- **`odoo_models`** — list of Odoo model technical names referenced in this skill (e.g. `account.move`, `res.partner`). Helps semantic search.
- **`tools`** — list of LLM tool names the skill relies on (e.g. `odoo_record_retriever`, `technical_skill_retriever`). Informational only.

## File placement

- Skills for the `llm_skills` module itself (meta/management skills): `llm_skills/skills/`
- Skills for a project module: `<module_name>/skills/` (e.g. `whatsapp_llm/skills/`)
- File name must match the `id` field: `{id}.md`

## Sync behavior

On every Odoo boot or module upgrade, the loader reads all `.md` files in its configured path, computes a SHA-256 hash of the content, and only re-processes files whose hash has changed. Removing a file from disk deactivates the corresponding `llm.skill.document` record (sets `active=False`) but does not delete it.

## Notes

- Keep each skill focused on one business question. Prefer many small skills over one large skill.
- The full file including frontmatter is embedded — write the frontmatter thoughtfully as it improves semantic recall.
- Do not add a `version` field to the frontmatter — content hash is used for change detection instead.
