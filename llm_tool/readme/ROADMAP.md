Known limitations:

- **Consent is advisory.** `requires_user_consent` is read in one place, where
  it adds instructions to the system prompt. No execution path checks it, so a
  model that ignores the instruction still runs the tool.
  ([#86](https://github.com/apexive/odoo-llm/issues/86); a fix is proposed in
  [#264](https://github.com/apexive/odoo-llm/pull/264).)
- **`mcp` is an unpinned dependency.** Its 2.x release moved
  `mcp.server.fastmcp` and renamed the wire fields, which breaks schema
  generation and tool definitions on a fresh install.
  ([#263](https://github.com/apexive/odoo-llm/pull/263))
- **OCA compliance is in progress.** This module is the first taken through the
  checklist; the remaining modules are still to do.
  ([#213](https://github.com/apexive/odoo-llm/issues/213))
