# Frontend Field Reference Audit - Related Record Fields

## Summary

✅ **All frontend references to related record fields have been properly updated to use `res_model` and `res_id`.**

## Field Usage Patterns

### 1. Thread Type Checking (✅ Correct - Uses `model`)

These references check if a thread is an LLM thread and should use `thread.model === "llm.thread"`:

- `llm_store_service.js:34` - `activeThread?.model === "llm.thread"`
- `llm_store_service.js:45` - `thread.model === "llm.thread"`
- `llm_store_service.js:138` - `model: "llm.thread"`
- `llm_store_service.js:324` - `activeThread?.model === "llm.thread"`
- `composer_patch.js:31` - `thread?.model === "llm.thread"`
- `thread_patch.js:28` - `thread?.model === "llm.thread"`
- `llm_chat_container.js:40` - `activeThread?.model === "llm.thread"`
- `llm_thread_header.js:46` - `activeThread?.model === "llm.thread"`

**Why correct:** These are checking the record type identifier, not the related record's model.

### 2. Related Record Access (✅ Updated - Uses `res_model` and `res_id`)

These references access the linked Odoo record and now correctly use `res_model` and `res_id`:

**llm_related_record.js:**

- Line 53: `return Boolean(this.props.thread.res_model && this.props.thread.res_id);`
- Line 80: `this.props.thread.res_model` (name_get call)
- Line 82: `[[this.props.thread.res_id]]` (name_get parameter)
- Line 101: `if (!this.props.thread.res_model)` (icon check)
- Line 124: `return iconMap[this.props.thread.res_model]` (icon lookup)
- Line 142: `res_model: this.props.thread.res_model` (doAction)
- Line 143: `res_id: this.props.thread.res_id` (doAction)
- Line 224: `` `${this.props.thread.res_model} #${this.props.thread.res_id}` `` (display name)

**llm_related_record.xml:**

- Line 12: `'Open ' + props.thread.res_model + ' #' + props.thread.res_id` (button title)
- Line 38: `t-esc="props.thread.res_model"` (fallback display)
- Line 39: `t-esc="props.thread.res_id"` (fallback display)

## Backend Serialization

**llm_thread.py (\_thread_to_store method):**

```python
thread_data = {
    "id": thread.id,
    "model": "llm.thread",  # Record type identifier (never changes)
    "name": thread.name,
    "write_date": thread.write_date,
    "channel_type": "llm_chat",
}

# Related record fields (for linking threads to Odoo records)
# Use res_model to avoid conflict with "model": "llm.thread"
if thread.model:
    thread_data["res_model"] = thread.model
if thread.res_id:
    thread_data["res_id"] = thread.res_id
```

## Key Insight

The confusion came from Odoo's naming convention:

| Backend Field                    | Frontend Key | Purpose                                           |
| -------------------------------- | ------------ | ------------------------------------------------- |
| `_name` (model's technical name) | `model`      | Record type identifier (e.g., "llm.thread")       |
| `model` (Char field)             | `res_model`  | Related record's model name (e.g., "res.partner") |
| `res_id` (Many2oneReference)     | `res_id`     | Related record's ID                               |

This matches Odoo's standard pattern in the mail system where:

- `model` = the type of the current record
- `res_model` + `res_id` = reference to another record

## Verification Checklist

- ✅ All type checks use `thread.model === "llm.thread"`
- ✅ All related record access uses `thread.res_model` and `thread.res_id`
- ✅ Backend serialization includes both fields without collision
- ✅ No mixed usage of old `thread.model` for related records
- ✅ Templates updated to use correct property paths
- ✅ No other modules reference these fields directly

## Files Verified

1. `llm_thread/static/src/services/llm_store_service.js`
2. `llm_thread/static/src/patches/composer_patch.js`
3. `llm_thread/static/src/patches/thread_patch.js`
4. `llm_thread/static/src/patches/chatter_patch.js`
5. `llm_thread/static/src/components/llm_chat_container/llm_chat_container.js`
6. `llm_thread/static/src/components/llm_thread_header/llm_thread_header.js`
7. `llm_thread/static/src/components/llm_related_record/llm_related_record.js`
8. `llm_thread/static/src/components/llm_related_record/llm_related_record.xml`
9. `llm_thread/static/src/components/llm_tool_message/llm_tool_message.js`
10. `llm_thread/static/src/client_actions/llm_chat_client_action.js`
11. `llm_thread/models/llm_thread.py`

## No Changes Needed In

- **llm_assistant module** - Doesn't access related record fields
- **Other LLM modules** - No direct thread property access
