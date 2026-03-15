Validate an Odoo module for common issues and compliance.

## Module: $ARGUMENTS

## Checks to Perform

### 1. Manifest Validation

Read `{module}/__manifest__.py` and verify:

- Version format is `18.0.X.Y.Z`
- All dependencies exist as module directories
- Required fields present: name, version, depends, license
- license is "LGPL-3"

### 2. Security Files

Check `{module}/security/`:

- `ir.model.access.csv` exists and has valid format
- All models referenced exist in `{module}/models/`
- Security XML files (if any) have valid group references

### 3. View Syntax (Odoo 18.0 Compliance)

Scan all XML files in `{module}/views/` for:

- `<tree>` tags (should be `<list>`)
- `attrs=` attributes (should use direct attributes)
- `states=` on buttons (should use `invisible=`)
- Deprecated `<data>` wrapper tags

### 4. Python Code Quality

Run linting check:

```bash
ruff check {module} --select=E,F,B
```

Check for deprecated patterns:

- `name_get()` method (removed in 18.0)
- `message_format()` method (removed in 18.0)
- `from odoo import registry` (should be `from odoo.modules.registry import Registry`)

### 5. Static Assets

Verify existence of:

- `{module}/static/description/icon.png`
- `{module}/static/description/index.html` (for App Store)

### 6. Documentation

Check for:

- `{module}/README.md` or `{module}/readme/DESCRIPTION.rst`
- `{module}/changelog.rst` - version matches manifest

### 7. App Store HTML Compliance

If `static/description/index.html` exists, check for violations:

- DOCTYPE, html, head, body tags (not allowed in App Store)
- `rgba()` colors (use hex only)
- CSS transitions, transforms, animations
- `linear-gradient` (not allowed)
- Inline JavaScript

## Output

Provide a report with:

- PASS/FAIL status for each check
- Specific issues found with file:line references
- Suggested fixes for each issue
