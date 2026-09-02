Tools are listed under the LLM menu. Each record carries:

- **Name and description** — what the model sees. The description is the main
  lever over whether a tool gets chosen correctly.
- **Input schema** — leave empty to generate it from the method signature, or
  set it to override what is advertised.
- **Behaviour hints** — `read_only_hint`, `idempotent_hint`,
  `destructive_hint` and `open_world_hint`, emitted as the Model Context
  Protocol annotations of the same name. Defaults are conservative:
  not read-only, not idempotent, destructive, open-world.
- **Requires user consent** — see below.
- **Auto update** — when set, the record is refreshed from the decorator on
  every restart. Clear it to manage a tool's configuration by hand.

**Consent.** `requires_user_consent` drives the consent configuration
(`llm.tool.consent.config`), which injects instructions into the system prompt
asking the model to obtain permission before calling the tool. Exactly one
configuration record is active at a time. Note that this operates on the prompt:
it asks the model to request consent, and does not by itself prevent execution.

Of the six generic tools, the record creator, updater, unlinker and model
method executor ship with consent required; the retriever and inspector do not.
