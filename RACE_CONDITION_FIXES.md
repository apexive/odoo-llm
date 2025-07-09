# Race Condition Fixes and Prompt Argument Improvements

This document outlines the changes made to fix race conditions and improve prompt argument presentation in the LLM generation system.

## Issues Identified

### 1. Race Conditions in Form Loading

**Problem**: The media form component had several race conditions where form fields were being initialized before the schema was fully loaded, causing empty forms or incorrect field rendering.

**Location**: `llm_generate/static/src/components/llm_media_form/llm_media_form.js`

**Root Causes**:
- `_initializeFormValues()` was called immediately after `_loadThreadConfiguration()` without waiting for completion
- `get formFields()` and `get inputSchema()` could execute while data was still loading
- Context changes triggered reloads without proper loading state management

### 2. Schema Computation Race Conditions

**Problem**: The computed field `input_schema_json` on prompts could be inconsistent when `template` and `arguments_json` fields were updated independently.

**Location**: `llm_assistant/models/llm_prompt.py`

**Root Causes**:
- Template arguments were not automatically synchronized with the arguments schema
- No validation to ensure template-schema consistency
- Manual updates to either field could leave the other field out of sync

### 3. Missing Prompt Argument Auto-Detection

**Problem**: When prompts defined arguments in templates, these weren't automatically detected and presented in forms unless manually configured.

**Root Causes**:
- Auto-detection was available but not automatically triggered
- New prompts or template changes didn't update schemas
- No clear indication of which schema source was being used

## Solutions Implemented

### 1. Fixed Async Race Conditions in Media Form

**Changes Made**:

```javascript
// Before - Race condition
async _handleContextChange() {
    await this._loadThreadConfiguration();
    this._initializeFormValues(); // Could execute before schema loaded
}

// After - Proper async handling
async _handleContextChange() {
    this.state.isLoading = true;
    try {
        await this._loadThreadConfiguration();
        this._initializeFormValues();
    } finally {
        this.state.isLoading = false;
    }
}
```

**Key Improvements**:
- Added proper loading state management
- Prevented form field generation during loading
- Added loading indicators in getters to prevent premature rendering
- Ensured form initialization waits for schema loading

### 2. Enhanced Prompt Argument Auto-Detection

**Changes Made**:

```python
@api.model_create_multi
def create(self, vals_list):
    prompts = super().create(vals_list)
    for prompt in prompts:
        if prompt.template:
            prompt.auto_detect_arguments()  # Auto-detect on creation
    return prompts

def write(self, vals):
    result = super().write(vals)
    if 'template' in vals:
        for prompt in self:
            prompt.auto_detect_arguments()  # Auto-detect on template changes
    return result
```

**Key Improvements**:
- Automatic argument detection on prompt creation
- Automatic argument detection when templates are modified
- Schema synchronization before computing input schemas
- Default new arguments as required (more explicit)

### 3. Improved Schema Source Transparency

**Changes Made**:

```javascript
get schemaSource() {
    if (this.state.isLoading) {
        return { type: 'loading', name: 'Loading...' };
    }

    if (this.state.threadConfig.input_schema && 
        Object.keys(this.state.threadConfig.input_schema).length > 0) {
        return {
            type: 'prompt',
            name: this.thread?.prompt_id?.name || 'Selected Prompt'
        };
    }
    
    // ... additional logic
}
```

**Key Improvements**:
- Clear indication of which schema source is being used (Prompt vs Model vs None)
- Visual badges showing schema source type
- Warning messages when no schema is available
- Better user feedback about form configuration

### 4. Enhanced Thread Schema Handling

**Changes Made**:

```python
def get_input_schema(self):
    """Get input schema for generation forms."""
    self.ensure_one()

    # Priority order:
    # 1. Assistant's prompt schema (if assistant selected)
    # 2. Thread's direct prompt schema (if prompt directly selected)
    # 3. Model's default schema
    
    # Check assistant's prompt first
    if hasattr(self, 'assistant_id') and self.assistant_id and self.assistant_id.prompt_id:
        prompt_schema = self._ensure_dict(self.assistant_id.prompt_id.input_schema_json)
        if prompt_schema and prompt_schema.get('properties'):
            return prompt_schema
    
    # ... additional logic
```

**Key Improvements**:
- Clear priority order for schema resolution
- Better handling of assistant vs direct prompt schemas
- Improved default value merging from schema and context
- Enhanced error handling and fallbacks

### 5. UI/UX Improvements

**Template Changes**:
- Added schema source indicator in form header
- Improved loading states with proper spinners
- Added warning messages for missing schemas
- Better separation of loading vs content states
- Enhanced error messaging

## Testing

Created comprehensive tests to verify the fixes:

### 1. Prompt Argument Tests (`llm_assistant/tests/test_prompt_arguments.py`)
- Auto-detection on creation and updates
- Schema synchronization
- Argument validation
- Edge cases and error handling

### 2. Thread Schema Tests (`llm_generate/tests/test_thread_schema.py`)
- Schema priority resolution
- Form default handling
- Input preparation with templates
- Error handling and fallbacks

## Impact

### Before the Changes
- Forms could render empty while loading
- UI would flash/jump as fields populated asynchronously
- Prompt arguments had to be manually configured
- No clear indication of schema source
- Race conditions causing inconsistent form states

### After the Changes
- Smooth loading experience with proper loading states
- Automatic argument detection and schema synchronization
- Clear transparency about schema sources
- Consistent form behavior across different scenarios
- Comprehensive test coverage for edge cases

## Future Improvements

1. **Real-time Template Validation**: Add live validation as users type in templates
2. **Schema Migration**: Tool to migrate existing prompts to new auto-detection system
3. **Advanced Argument Types**: Support for more complex argument types (arrays, objects)
4. **Schema Versioning**: Track schema changes over time for better debugging
5. **Performance Optimization**: Cache computed schemas for better performance

## Migration Notes

These changes are backward compatible:
- Existing prompts will automatically get argument detection on next save
- Existing forms will continue to work with improved loading behavior
- No database migrations required
- All changes are additive, not breaking

The improvements ensure that prompt arguments are properly and consistently presented in forms while eliminating race conditions that could cause poor user experience.
