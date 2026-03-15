Fix App Store HTML compliance issues for an Odoo module.

## Module: $ARGUMENTS

## Reference

See ODOO_APP_STORE_HTML_GUIDE.md for complete guidelines.

## Steps

### 1. Read Current HTML

Read `{module}/static/description/index.html`

### 2. Identify Violations

Check for and fix these issues:

**Structure violations:**

- Remove `<!DOCTYPE html>`, `<html>`, `<head>`, `<body>` tags
- Keep only the content that would go inside `<body>`
- Remove `<meta>`, `<title>`, `<link>` tags

**CSS violations to fix:**

- `rgba(r,g,b,a)` → convert to hex colors (e.g., `#6f42c1`)
- `transition:` → remove entirely
- `transform:` → remove entirely
- `:hover` effects with transforms → remove
- `linear-gradient()` → use solid colors or remove
- `animation:` → remove entirely
- CSS variables (`var(--x)`) → replace with actual values

**JavaScript violations:**

- Remove any `onclick`, `onmouseover`, etc. attributes
- Remove `<script>` tags

**External resources:**

- Keep Bootstrap CSS CDN link (this is allowed)
- Remove other external JS/CSS that won't work

### 3. Preserve Styling

When removing effects, try to preserve the visual design:

- Keep colors (convert to hex)
- Keep spacing and layout
- Keep Bootstrap classes
- Replace hover effects with static styling

### 4. Output

Show the fixed HTML and list all changes made.

## Common Replacements

```
rgba(0,0,0,0.1) → #e5e5e5 (light gray for shadows)
rgba(111,66,193,0.1) → #f3eff8 (light purple)
linear-gradient(90deg, #6f42c1, transparent) → border-bottom: 3px solid #6f42c1
transition: transform 0.3s → (remove)
transform: translateY(-5px) → (remove)
```
