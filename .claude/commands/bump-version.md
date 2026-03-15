Bump the version of an Odoo module and update all related documentation.

## Module: $ARGUMENTS

If no module is specified, list all modules with their current versions from **manifest**.py.

## Steps to Follow

### 1. Read Current State

First, read these files for the specified module:

- `{module}/__manifest__.py` - get current version
- `{module}/changelog.rst` - if exists, get changelog format
- `{module}/README.md` - if exists
- `{module}/doc/index.rst` - if exists
- `{module}/static/description/index.html` - if exists

### 2. Ask User for Version Bump Type

Ask the user:

- **Bump type**: patch (x.x.X), minor (x.X.0), or major (X.0.0)?
- **Changes**: What changes should be documented?

Use these changelog tags:

- `[ADD]` - New feature
- `[FIX]` - Bug fix
- `[IMP]` - Improvement
- `[REM]` - Removed feature
- `[REF]` - Refactoring
- `[BREAKING]` - Breaking change
- `[MIGRATION]` - Migration-related
- `[SEC]` - Security fix

### 3. Update **manifest**.py

Update the `"version"` field. Format: `18.0.X.Y.Z`

- Major: increment X, reset Y and Z to 0
- Minor: increment Y, reset Z to 0
- Patch: increment Z

### 4. Update changelog.rst

Add new version entry at the TOP of the file:

```rst
18.0.X.Y.Z (YYYY-MM-DD)
~~~~~~~~~~~~~~~~~~~~~~~

* [TAG] Description of change
* [TAG] Another change
```

If changelog.rst doesn't exist, create it with the new entry.

### 5. Check Documentation for Outdated Information

Review these files and warn about potentially outdated content:

**README.md** - Check for:

- Version numbers that don't match new version
- Feature descriptions that may be outdated based on changes
- Installation/usage instructions that may need updating

**doc/index.rst** - Check for:

- Outdated usage examples
- Feature descriptions inconsistent with changes

**static/description/index.html** - Check for:

- Outdated feature lists
- Version references
- Screenshots that may be outdated
- Also warn about App Store HTML violations (DOCTYPE, rgba, transitions, etc.)

### 6. Summary

Provide a summary of:

- Files modified
- New version number
- Changelog entries added
- Any documentation that may need manual review

Do NOT make changes to README.md, doc/index.rst, or index.html automatically - only warn about potential issues and let the user decide what to update.
