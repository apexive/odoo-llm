---
name: odoo-skill-creator
description: >
  Use when a recurring Odoo configuration or operational pattern should be
  captured as a new skill file, or when the user asks to create, write, or add
  a skill. Trigger whenever the user mentions: new skill, create a skill, write
  a skill, save this pattern, remember this, or wants to preserve a solution
  for future reuse. Also trigger when you just solved a non-trivial problem
  that required discovery and you want to save the pattern.
---

# Create a New Odoo Skill

## When to create a skill

Create a skill when you have just solved a non-trivial Odoo problem and want to
preserve the pattern for future reuse. Good candidates:

- Multi-step configuration sequences (e.g. set up a WhatsApp account + assign an assistant)
- Non-obvious field names, domain syntax, or model relationships
- Wizard patterns that require a specific sequence of method calls
- Any pattern you had to discover via `odoo_model_inspector` rather than deduce

Do NOT create a skill for:

- One-off, user-specific operations
- Things trivially deducible from model fields
- Duplicates of existing skills (check first with `odoo_skill_searcher`)

## Skill file format

Each skill lives in its own directory under `skills/`:

```
skills/
└── your-skill-name/
    └── SKILL.md
```

**SKILL.md frontmatter (required fields):**

```yaml
---
name: your-skill-name          # kebab-case, max 64 chars, no spaces
description: >                 # max 1024 chars — THIS IS WHAT GETS EMBEDDED
  Use when... (describe the trigger condition, not what the skill does).
  Make this "pushy" — err toward loading when in doubt.
  Cover synonyms and alternate phrasings the user might use.
---

# Skill Title

Full markdown instructions here...
```

**Critical rules:**

- `name` must be unique (kebab-case, no spaces, no reserved words like `odoo_skill_searcher`)
- `description` must describe **when to use** the skill, not what it does
- Make descriptions trigger-happy: "Use when X, or when the user mentions Y or Z"
- Body goes after the frontmatter (below the closing `---`)

## Placement

Skills go in the `skills/` directory of the relevant addon.
For Odoo Admin Assistant patterns: `llm_skills/skills/your-skill-name/SKILL.md`

## After creating

The loader auto-discovers and syncs on the next Odoo start.
To sync immediately: go to **LLM → Skills → Loaders** → "Sync Now" on the relevant loader.

Or trigger sync via the Admin Assistant:
> "Sync the llm_skills loader"

Then verify the skill was loaded:
> `odoo_skill_searcher("what the skill does")`
