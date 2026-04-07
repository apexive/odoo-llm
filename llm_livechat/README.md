# LLM Livechat

Odoo module that integrates LLM assistants with the live chat feature.

## Features

- Automatically trigger AI responses to visitor messages in live chat channels
- Optional AI greeting when a chat session starts
- Rate limiting to prevent message loops
- Simple emoji code conversion for friendly responses

## Message Formatting

The module provides simple emoji code conversion for LLM responses.

### Emoji Support

Emoji codes (Slack/Discord style) are automatically converted to Unicode:

- `:wave:` → 👋
- `:rocket:` → 🚀
- `:bulb:` → 💡
- `:checkmark:` → ✅
- `:fire:` → 🔥
- `:tada:` → 🎉

Over 70 common emoji codes are supported.

### Assistant Configuration

For best visual results, encourage your assistant to use emoji codes:

```
Instructions:
- Use emoji codes to make responses friendly (:wave: :rocket: :bulb:)
- Keep responses clear and concise
- Structure information with line breaks
```

### No HTML/Markdown Processing

The module intentionally does NOT process HTML or Markdown to avoid:
- Double-escaping issues
- Security risks
- Complexity

LLM responses are displayed as-is, with only emoji codes converted.

## Loop Protection

The module includes multiple safeguards to prevent infinite message loops:

- The `llm_response=True` context flag prevents re-triggering when the bot posts
- Bot and operator messages are ignored (only visitor messages trigger AI responses)
- Rate limiting: if 3 or more visitor messages are detected in a 5-second window (including the current one), the response is skipped
