# LLM Skills

Filesystem-loaded skill documents for LLM assistants — versioned in Git, RAG-retrieved at runtime.

**Module Type:** 🧠 Knowledge Infrastructure

## What It Does

`llm_skills` turns markdown files in your addon's `skills/` directory into a RAG-powered long-term memory for your LLM assistants. Skills are Odoo-specific patterns — "how to query overdue invoices", "how to send a WhatsApp message", "when to create a new skill" — that the assistant retrieves before acting, rather than guessing from base training.

```
skills/my-pattern.md  ──sync──▶  llm.skill.document  ──embed──▶  pgvector  ──retrieve──▶  LLM
```

Skills are versioned alongside your code. When you restart Odoo, changed files are re-embedded; unchanged files are skipped via SHA-256 hash.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        MCP Clients                              │
│   Claude Desktop  │  Claude Code  │  Cursor  │  Odoo Assistant  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ MCP / tool call
                           ▼
              ┌────────────────────────────┐
              │   technical_skill_retriever │  ← @llm_tool
              │       (llm_skills)          │
              └────────────────┬───────────┘
                               │ vector similarity search
                               ▼
              ┌────────────────────────────┐
              │   llm.knowledge.collection  │
              │   "Odoo Technical Skills"   │  ← pgvector
              └────────────────┬───────────┘
                               │
              ┌────────────────▼───────────┐
              │      llm.skills.loader      │  ← auto-discovered per addon
              │   skills/*.md  ──sync──▶   │
              │   llm.skill.document        │
              └────────────────────────────┘
```

## Automated Setup

`llm_skills` configures itself completely during install/upgrade — no manual steps needed if `OPENAI_API_KEY` is set in your `.env`:

| Step | What happens |
|---|---|
| 1 | OpenAI provider found or created |
| 2 | API key read from `OPENAI_API_KEY` env var → written to provider + `ir.config_parameter` |
| 3 | All OpenAI models fetched live from the API and upserted |
| 4 | pgvector store created (`Odoo PgVector`) |
| 5 | `Odoo Technical Skills` collection created with `text-embedding-3-small` |
| 6 | On boot: all addon `skills/` directories auto-discovered → loaders created → skills synced and embedded |

If no API key is available at install time, steps 3–6 are deferred. Set the key later and upgrade the module to complete setup.

**Alternative to env var:** create a system parameter before install:
```
Settings → Technical → System Parameters → New
Key:   llm_skills.openai_api_key
Value: sk-...
```

## Writing Skills

A skill is a markdown file with YAML frontmatter in any installed addon's `skills/` directory:

```markdown
---
id: find-overdue-invoices
title: Find Overdue Customer Invoices
tags: [invoicing, accounting, partners]
odoo_models: [account.move, res.partner]
tools: [odoo_record_retriever]
---

## When to use
When asked about unpaid or overdue customer invoices.

## Solution
Query `account.move` with domain:
`[('move_type','=','out_invoice'),('payment_state','not in',['paid','reversed']),('invoice_date_due','<', fields.Date.today())]`

Key fields: `name`, `partner_id`, `amount_residual`, `invoice_date_due`.

## Notes
Sort by `invoice_date_due asc` to surface oldest first.
```

**Rules:**
- `id` must be stable (kebab-case, matches filename stem) — never change it after creation
- One business question per skill — keep them small and focused
- Full file including frontmatter is embedded — write it thoughtfully

The loader picks up new/changed files on next boot or "Sync Now" button.

## Skill Directories

Skills live alongside their module code:

```
llm_skills/skills/          ← meta-skills about the skills system
whatsapp_llm/skills/        ← WhatsApp conversation patterns
llm_tool_account/skills/    ← SYSCOHADA accounting patterns
your_module/skills/         ← your domain patterns
```

All `skills/` directories in installed addons are auto-discovered and loaded into the `Odoo Technical Skills` collection by default. To use a separate collection for a module (e.g. `WhatsApp Skills`), edit the auto-created loader record in **LLM → Skills → Loaders** and change the collection.

## Exposing Skills via MCP

`llm_skills` depends on `llm_mcp_server`, so the `technical_skill_retriever` tool is automatically available to any MCP client connected to your Odoo instance.

### 1. Generate an MCP API Key

Each user generates their own key tied to their Odoo permissions:

1. Click your **avatar** (top-right) → **My Profile**
2. Scroll to **Account Security** → click **New MCP Key**
3. Enter a description (e.g. `"Claude Desktop — skills"`) and confirm your password
4. Copy the key immediately — it cannot be retrieved later

Or navigate to **LLM → Configuration → MCP Server → New MCP Key**.

### 2. Connect Claude Desktop

Paste into `~/.config/claude_desktop/claude_desktop_config.json` (Linux/macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "odoo-ordomatics": {
      "type": "stdio",
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://localhost:8069/mcp",
        "--header",
        "Authorization: Bearer YOUR_API_KEY"
      ],
      "env": { "MCP_TRANSPORT": "streamable-http" }
    }
  }
}
```

### 3. Connect Claude Code

```bash
claude mcp add-json odoo-ordomatics '{
  "type": "stdio",
  "command": "npx",
  "args": ["-y", "mcp-remote", "http://localhost:8069/mcp",
           "--header", "Authorization: Bearer YOUR_API_KEY"],
  "env": {"MCP_TRANSPORT": "streamable-http"}
}'
```

### 4. Connect Cursor / Codex / Other Clients

Any MCP-compatible client: connect to `http://localhost:8069/mcp` with header `Authorization: Bearer YOUR_API_KEY`.

### 5. Use the Skill Retriever

Once connected, the `technical_skill_retriever` tool is available. The assistant calls it automatically when it needs Odoo-specific guidance. You can also invoke it explicitly:

> "Before querying overdue invoices, retrieve the relevant skill first."

The tool requires a `collection_id`. Available collections and their IDs are injected into the tool schema description at runtime — the assistant picks the right one from context.

### Using Odoo's Built-in Assistants

To wire a skill collection to an Odoo assistant (chat UI, WhatsApp bot, etc.):

1. Go to **LLM → Configuration → Assistants** → open your assistant
2. Set **Technical Skills Collection** to `Odoo Technical Skills` (or your domain collection)
3. Add `technical_skill_retriever` to the assistant's **Tools**
4. The assistant will now retrieve relevant skills before acting

## Collections

| Collection | Purpose | Default for |
|---|---|---|
| `Odoo Technical Skills` | Generic Odoo patterns, meta-skills | All auto-discovered loaders |
| `WhatsApp Skills` | WhatsApp/Meta API patterns | `whatsapp_llm` loader (manual reassignment) |

To reassign a loader to a different collection: **LLM → Skills → Loaders** → open loader → change **Target Collection**.

## Chunking Strategy

Skill documents are embedded as single chunks (`target_chunk_size=2000`, `overlap=0`), regardless of the collection's default chunk size. This preserves the semantic coherence of each skill — a skill is one atomic unit of knowledge and should never be split mid-context. The 2000-token ceiling acts as a safety valve for oversized skills.

## Module Structure

```
llm_skills/
├── models/
│   ├── llm_provider.py          # OpenAI provider + model auto-setup
│   ├── llm_knowledge_collection.py  # _create_meta_skills_collection()
│   ├── llm_skill_document.py    # llm.skill.document model
│   ├── llm_resource.py          # chunk size override for skill resources
│   ├── llm_skills_loader.py     # sync engine + auto-discovery
│   ├── llm_assistant.py         # technical_skills_collection_id field
│   └── llm_tool_skill_retriever.py  # technical_skill_retriever @llm_tool
├── data/
│   ├── llm_tool_data.xml        # tool record
│   ├── llm_provider_data.xml    # OpenAI provider + model setup
│   └── llm_store_data.xml       # pgvector store + collection
├── skills/                      # meta-skills about the skills system
│   ├── skill-authoring-guide.md
│   ├── skill-lifecycle.md
│   └── skill-when-to-create.md
└── views/
    ├── llm_skill_document_views.xml
    ├── llm_skills_loader_views.xml
    ├── llm_assistant_views.xml
    └── menu.xml
```

## Troubleshooting

**Skills not showing up after install?**

- Check that `OPENAI_API_KEY` is set in `.env` and the container was restarted after adding it
- Go to **LLM → Skills → Loaders** — if no loaders exist, the collection wasn't created yet
- Set the API key and upgrade `llm_skills`: `odoo-bin -d odoo -u llm_skills`

**Skill retriever returns no results?**

- Verify the loader's `last_sync` timestamp is recent
- Check the loader's skill count stat button — if 0, sync failed
- Open **LLM → Knowledge → Collections → Odoo Technical Skills** → check chunk count
- Confirm the collection's embedding model is set and the resource states are `ready`

**MCP key not working?**

- Verify the key format: `Authorization: Bearer <key>` (no extra spaces)
- Check the user has access to LLM tools (**LLM → Tools** — tools must be active)
- Test connectivity with MCP Inspector: `https://modelcontextprotocol.io/docs/tools/inspector`
