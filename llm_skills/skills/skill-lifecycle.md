---
id: skill-lifecycle
title: Skill Pipeline — From File to RAG Retrieval
tags: [skills, meta, architecture, rag]
odoo_models: [llm.skill.document, llm.skills.loader, llm.resource, llm.knowledge.collection]
tools: [technical_skill_retriever]
---

# Skill Pipeline — From File to RAG Retrieval

## When to use
Use this skill when you need to understand how a skill `.md` file becomes available for LLM retrieval, or when debugging why a skill is not being found by the retriever.

## Solution

The full pipeline from file to retrieval has four stages:

### 1. Authoring — `.md` file on disk
A skill is a Markdown file with YAML frontmatter stored in a module's `skills/` directory. The file is the source of truth. It lives in Git alongside the module code.

### 2. Sync — `llm.skills.loader`
On every Odoo boot or module upgrade, `llm.skills.loader._register_hook()` triggers `_sync_skills()` for all loaders with `auto_sync_on_boot=True`. For each `.md` file:
- SHA-256 hash is computed and compared against `llm.skill.document.content_hash`
- If unchanged → skipped
- If changed or new → `llm.skill.document` record is created/updated, then `llm.resource` is created/updated and its state is reset to `pending` so the RAG pipeline re-processes it
- If file removed from disk → `llm.skill.document.active` is set to `False`

### 3. RAG processing — `llm.resource`
Each `llm.skill.document` is pointed to by an `llm.resource` record in the loader's target `llm.knowledge.collection`. The RAG pipeline:
- Calls `llm_get_fields()` on the skill document → returns the full markdown content
- Chunks the content
- Embeds the chunks using the collection's embedding model
- Stores vectors for retrieval

### 4. Retrieval — `technical_skill_retriever` tool
When the LLM needs a skill, it calls the `technical_skill_retriever` tool with a natural language query. The tool:
- Resolves the assistant's `technical_skills_collection_id`
- Runs a vector similarity search against the embedded skill chunks
- Returns the top-k matching skill documents above the similarity cutoff (default: 0.35)

## Variants

**Manual sync:** Use the "Sync Now" button on the `llm.skills.loader` form view to trigger a sync without restarting Odoo.

**Checking sync status:** Open the loader record → the "Skills" stat button shows the count of active skill documents. Click it to inspect individual records and their `content_hash`.

**Debugging retrieval:** If a skill is not being found, check:
1. Is the `llm.skill.document` record active?
2. Is the associated `llm.resource` in `done` state?
3. Is the loader's `collection_id` set as the assistant's `technical_skills_collection_id`?
4. Is the query semantically close enough to the skill content? (similarity cutoff: 0.35)

## Notes

- Each project module has its own loader record pointing to its own `skills/` path.
- Multiple loaders can target the same collection (e.g. shared technical skills collection).
- The `llm_skills` module itself ships management/meta skills in its own `skills/` directory with its own loader.
