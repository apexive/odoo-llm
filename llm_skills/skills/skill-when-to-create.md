---
id: skill-when-to-create
title: When to Create a New Skill vs Answer Directly
tags: [skills, meta, decision]
odoo_models: []
tools: [technical_skill_retriever]
---

# When to Create a New Skill vs Answer Directly

## When to use
Use this skill when deciding whether a user's question or a recurring pattern should be captured as a new skill file, or handled as a one-off answer.

## Solution

### Create a new skill when:
- The same business question has been asked more than once and required non-trivial lookup logic (which models, which filters, which fields)
- The answer involves Odoo-specific knowledge that is unlikely to be in the LLM's base training (custom modules, client-specific field names, business rules)
- The logic is reusable across multiple user contexts or sessions
- A correct answer was reached after debugging — capture it before it is forgotten

### Answer directly (no skill needed) when:
- The question is a one-off that won't recur
- The answer is trivially deducible from standard Odoo knowledge
- The question is about a user-specific situation with no generalizable pattern
- The skill would duplicate content already covered by an existing skill

### How to create the skill
1. Identify the stable `id` (kebab-case, matches the filename)
2. Write the `.md` file following `skill-authoring-guide`
3. Place it in the correct module's `skills/` directory
4. The loader will pick it up on next boot or "Sync Now"

### How to propose a skill to the user
When you identify that a pattern should be captured, say:
> "This looks like a recurring pattern. I can write a skill file for this so I remember how to handle it in future sessions. Should I create `skills/<id>.md` in `<module>/skills/`?"

## Notes

- Prefer creating skills eagerly — a small well-focused skill is cheap to store and highly valuable for recall.
- The skill system is the long-term memory of the assistant. Direct answers are forgotten at session end; skills persist across restarts.
- When in doubt, create the skill.
