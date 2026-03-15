# Related Record Bug Fix - Model Field Naming Collision & name_get Removal

## Problems Discovered

### 1. Field Name Collision

After implementing the Related Record component, we discovered that linked record data was not appearing in the frontend, and thread metadata (provider, model, write_date) was not displaying correctly.

### 2. name_get() Method Removed in Odoo 18.0

When testing the component, we encountered:

```
AttributeError: The method 'res.partner.name_get' does not exist
```

## Root Causes

### Problem 1: Field name collision in `_thread_to_store()` method

The `llm.thread` model has a `model` field that stores the related record's model name (e.g., "res.partner", "sale.order"). In the `_thread_to_store()` method, we were serializing this as:

```python
thread_data = {
    "id": thread.id,
    "model": "llm.thread",  # Record type identifier
    "name": thread.name,
    # ...
}

# Later in the method...
if thread.model:
    thread_data["model"] = thread.model  # ❌ OVERWRITES the record type!
```

This caused `"model": "llm.thread"` to be overwritten with the related record model name, breaking:

- Thread list rendering (expects `model: "llm.thread"`)
- Store lookups (can't find threads by type)
- All metadata display (provider, model, write_date)

### Problem 2: name_get() removed in Odoo 18.0

The `name_get()` method was deprecated and removed in Odoo 18.0. The component was calling:

```javascript
const result = await this.orm.call(this.props.thread.res_model, "name_get", [
  [this.props.thread.res_id],
]);
```

This fails on all models in Odoo 18.0.

## Solutions

### Solution 1: Use res_model Instead of model

Following Odoo's mail system conventions, we renamed the field in the serialized data from `"model"` to `"res_model"`:

### Backend Fix (llm_thread/models/llm_thread.py)

```python
# Related record fields (for linking threads to Odoo records)
# Use res_model to avoid conflict with "model": "llm.thread"
if thread.model:
    thread_data["res_model"] = thread.model  # ✅ No collision
if thread.res_id:
    thread_data["res_id"] = thread.res_id
```

### Frontend Fix (llm_related_record.js)

Updated all references from `props.thread.model` to `props.thread.res_model`:

```javascript
// Before
get hasRelatedRecord() {
    return Boolean(this.props.thread.model && this.props.thread.res_id);
}

// After
get hasRelatedRecord() {
    return Boolean(this.props.thread.res_model && this.props.thread.res_id);
}
```

### Template Fix (llm_related_record.xml)

```xml
<!-- Before -->
<button t-att-title="'Open ' + state.linkedModel + ' #' + state.linkedResId">

<!-- After -->
<button t-att-title="'Open ' + props.thread.res_model + ' #' + props.thread.res_id">
```

### Solution 2: Replace name_get() with searchRead()

Changed the display name loading to use `searchRead()` with `display_name` field:

**Before (Odoo 16.0 pattern):**

```javascript
const result = await this.orm.call(this.props.thread.res_model, "name_get", [
  [this.props.thread.res_id],
]);

if (result && result.length > 0) {
  this.state.relatedRecordDisplayName = result[0][1]; // name_get returns [id, name] tuples
}
```

**After (Odoo 18.0 pattern):**

```javascript
// Use searchRead instead of name_get (removed in Odoo 18.0)
const result = await this.orm.searchRead(
  this.props.thread.res_model,
  [["id", "=", this.props.thread.res_id]],
  ["display_name"]
);

if (result && result.length > 0) {
  this.state.relatedRecordDisplayName = result[0].display_name;
}
```

## Files Changed

1. `llm_thread/models/llm_thread.py` - Lines 445-450 (res_model field)
2. `llm_thread/static/src/components/llm_related_record/llm_related_record.js` - Lines 71-95 (searchRead), multiple res_model references
3. `llm_thread/static/src/components/llm_related_record/llm_related_record.xml` - Lines 12, 38-39 (res_model)

## Why res_model?

This follows Odoo's standard pattern in the mail system:

- `model` = the record type identifier (e.g., "llm.thread", "mail.message")
- `res_model` = the model of a related/linked record
- `res_id` = the ID of the related/linked record

See: `odoo/addons/mail/models/mail_thread.py` for examples of this pattern.

### Solution 3: Centralize Business Logic in Service Layer

Following proper architectural patterns, we moved the link/unlink logic to `llm_store_service.js`:

**Service Layer (llm_store_service.js):**

```javascript
// Link a record to a thread
async linkRecordToThread(threadId, model, recordId) {
  try {
    // Update database
    await orm.write("llm.thread", [threadId], {
      model: model,
      res_id: recordId,
    });

    // Update the thread object in mailStore for immediate reactivity
    const thread = mailStore.Thread.get({
      model: "llm.thread",
      id: threadId,
    });

    if (thread) {
      Object.assign(thread, {
        res_model: model,
        res_id: recordId,
      });
    }

    notification.add("Record linked successfully", { type: "success" });
    return true;
  } catch (error) {
    console.error("Error linking record:", error);
    notification.add("Failed to link record", { type: "danger" });
    return false;
  }
}
```

**Component Layer (llm_related_record.js):**

```javascript
async linkRecord(model, recordId) {
  // Delegate to llm.store service for business logic
  const success = await this.llmStore.linkRecordToThread(
    this.props.thread.id,
    model,
    recordId
  );

  if (success) {
    // Only handle UI-specific logic (reload display name)
    await this.loadRelatedRecordDisplayName();
  }
}
```

**Why this architecture is better:**

- ✅ **Separation of concerns** - Business logic in service, UI logic in component
- ✅ **Reusability** - Other components can link/unlink records using the same service methods
- ✅ **Testability** - Service methods can be tested independently
- ✅ **Maintainability** - All state management centralized in one place
- ✅ **Consistency** - Follows the same pattern as `createNewThread()`, `selectThread()`, etc.
- ✅ **Reactivity** - `Object.assign()` on thread object triggers immediate UI updates

## Testing

After this fix, the following should work:

1. ✅ Thread list shows correct metadata (write_date, provider, model)
2. ✅ Thread header displays provider and model dropdowns
3. ✅ Link button appears when no record is linked
4. ✅ After linking, Unlink button appears immediately (no reload needed)
5. ✅ Linked record icon and name display correctly
6. ✅ Opening linked record navigates to correct form view
7. ✅ Unlinking removes the link and shows Link button again
8. ✅ UI updates are instant (reactive) without page reload

## Lessons Learned

1. **Always check Odoo conventions** - When in doubt, look at how core modules (especially `mail`) handle similar scenarios
2. **Field naming matters** - Keys in store data have specific meanings; don't overwrite them
3. **Test with real data** - The bug only appeared when actually linking records, not in initial component display
4. **Store structure is critical** - The frontend `mail.store` expects specific field names and structures
5. **name_get() is gone in Odoo 18.0** - Always use `searchRead()` with `display_name` field instead
6. **Check migration guides** - Major version upgrades remove deprecated methods
7. **Direct object updates for reactivity** - Use `Object.assign()` on reactive props for instant UI updates
8. **Study similar components** - The thread header component showed us the correct reactivity pattern
