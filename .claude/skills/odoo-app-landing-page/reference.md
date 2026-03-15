# Odoo App Store Landing Page - Quick Reference

## Quick CSS Reference Table

| Category              | ❌ Don't Use                                   | ✅ Use Instead                   |
| --------------------- | ---------------------------------------------- | -------------------------------- |
| **Flexbox Alignment** | `style="align-items:center"`                   | `class="align-items-center"`     |
| **Flex Justify**      | `style="justify-content:center"`               | `class="justify-content-center"` |
| **Colors**            | `rgba(135,90,123,0.1)`                         | `#f5efff`                        |
| **Shadows**           | `style="box-shadow:0 4px 6px rgba(0,0,0,0.1)"` | `class="shadow-sm"`              |
| **Transitions**       | `style="transition:all 0.3s"`                  | ❌ Not supported                 |
| **Transforms**        | `style="transform:translateY(-5px)"`           | ❌ Not supported                 |
| **Links**             | `<a href="https://github.com">GitHub</a>`      | `<code>github.com/repo</code>`   |
| **Special Chars**     | `→` (unicode)                                  | `&rarr;` (HTML entity)           |
| **Gradients**         | `linear-gradient(...)`                         | Use solid colors                 |
| **Flex Gap**          | `style="gap:1rem"`                             | Use margin classes `mb-3`        |

## HTML Entities Reference

| Character | HTML Entity | Numeric   | Name        |
| --------- | ----------- | --------- | ----------- |
| →         | `&rarr;`    | `&#8594;` | Right arrow |
| ←         | `&larr;`    | `&#8592;` | Left arrow  |
| —         | `&mdash;`   | `&#8212;` | Em dash     |
| –         | `&ndash;`   | `&#8211;` | En dash     |
| •         | `&bull;`    | `&#8226;` | Bullet      |
| ©         | `&copy;`    | `&#169;`  | Copyright   |
| ®         | `&reg;`     | `&#174;`  | Registered  |
| ™         | `&trade;`   | `&#8482;` | Trademark   |
| &         | `&amp;`     | `&#38;`   | Ampersand   |
| "         | `&quot;`    | `&#34;`   | Quote       |

## Safe Color Palette (Hex Only)

### Primary

```
#875A7B    - Odoo Purple (primary)
#71639e    - Odoo Purple (alternative)
#5b4c7d    - Dark Purple
```

### Text Colors

```
#212529    - Very dark (headings)
#333       - Dark gray (body text)
#495057    - Medium dark
#6c757d    - Medium gray
#868e96    - Light gray
#fff       - White
```

### Backgrounds

```
#ffffff    - Pure white
#f8f9fa    - Very light gray
#f5efff    - Light purple tint
#f7f2fa    - Lighter purple tint
#faf8fc    - Very subtle purple
```

### Semantic Colors

```
#28a745    - Success green
#155724    - Dark success
#dc3545    - Danger red
#721c24    - Dark danger
#ffc107    - Warning yellow
#856404    - Dark warning
#17a2b8    - Info blue
#0c5460    - Dark info
#007bff    - Primary blue
```

## Bootstrap 5 Grid Breakpoints

| Class       | Breakpoint | Width    |
| ----------- | ---------- | -------- |
| `col-*`     | All        | < 576px  |
| `col-sm-*`  | Small      | ≥ 576px  |
| `col-md-*`  | Medium     | ≥ 768px  |
| `col-lg-*`  | Large      | ≥ 992px  |
| `col-xl-*`  | X-Large    | ≥ 1200px |
| `col-xxl-*` | XX-Large   | ≥ 1400px |

## Common Responsive Patterns

```html
<!-- 1 column mobile, 2 tablet, 3 desktop -->
<div class="col-lg-4 col-md-6 col-12">
  <!-- 1 column mobile, 2 tablet, 4 desktop -->
  <div class="col-lg-3 col-md-6 col-12">
    <!-- 2 column mobile, 3 tablet, 6 desktop -->
    <div class="col-lg-2 col-md-4 col-6">
      <!-- Always 2 columns (50% each) -->
      <div class="col-md-6 col-12"></div>
    </div>
  </div>
</div>
```

## Bootstrap Utility Classes (Safe to Use)

### Display

```
d-none, d-block, d-inline-block, d-flex, d-inline-flex
d-sm-*, d-md-*, d-lg-*, d-xl-* (responsive variants)
```

### Flexbox (Use Classes, NOT Inline Styles!)

```
d-flex
flex-row, flex-column
flex-wrap, flex-nowrap
justify-content-start, justify-content-center, justify-content-end
justify-content-between, justify-content-around
align-items-start, align-items-center, align-items-end
align-content-*, align-self-*
```

### Spacing (Margin/Padding)

```
m-0, m-1, m-2, m-3, m-4, m-5 (all sides)
mt-*, mb-*, ms-*, me-* (top, bottom, start, end)
mx-*, my-* (horizontal, vertical)
p-0 through p-5 (padding, same pattern)
g-4 (gap for grid)
```

### Sizing

```
w-25, w-50, w-75, w-100
h-25, h-50, h-75, h-100
mw-100, mh-100 (max width/height)
```

### Text

```
text-start, text-center, text-end
text-wrap, text-nowrap
text-lowercase, text-uppercase, text-capitalize
fw-light, fw-normal, fw-bold, fw-bolder (font weight)
fs-1 through fs-6 (font size)
```

### Borders & Shadows

```
border, border-0
border-top, border-bottom, border-start, border-end
rounded, rounded-circle, rounded-pill
shadow, shadow-sm, shadow-lg
```

### Colors (Use for backgrounds/text with Bootstrap classes)

```
text-primary, text-secondary, text-success, text-danger, text-warning, text-info
bg-primary, bg-secondary, bg-success, bg-danger, bg-warning, bg-info, bg-light, bg-dark
```

## Common Section Templates

### Hero with Centered Content

```html
<section style="padding:4rem 0 3rem">
  <div class="container">
    <div class="text-center" style="max-width:800px; margin:0 auto">
      <h1
        style="font-size:3rem; font-weight:800; color:#212529; margin-bottom:1.5rem"
      >
        Title
      </h1>
      <p style="font-size:1.25rem; color:#6c757d; margin-bottom:2rem">
        Description
      </p>
    </div>
  </div>
</section>
```

### Centered Heading + 3-Column Features

```html
<section class="mb-5">
  <h2
    class="text-center mb-4"
    style="font-size:2.5rem; font-weight:700; color:#71639e"
  >
    Section Title
  </h2>
  <p class="text-center mb-5" style="font-size:1.1rem; color:#6c757d">
    Subtitle
  </p>
  <div class="row g-4">
    <div class="col-md-4 col-12">
      <!-- Card -->
    </div>
    <div class="col-md-4 col-12">
      <!-- Card -->
    </div>
    <div class="col-md-4 col-12">
      <!-- Card -->
    </div>
  </div>
</section>
```

### Card with Icon

```html
<div class="card border-0 shadow-sm h-100" style="border-radius:16px">
  <div class="card-body p-4">
    <div
      class="bg-light d-flex align-items-center justify-content-center"
      style="width:56px; height:56px; border-radius:12px; margin-bottom:1.5rem"
    >
      <i class="fa fa-check" style="font-size:28px; color:#71639e"></i>
    </div>
    <h3
      style="font-size:1.25rem; font-weight:700; color:#212529; margin-bottom:1rem"
    >
      Card Title
    </h3>
    <p
      style="color:#6c757d; font-size:0.95rem; line-height:1.7; margin-bottom:0"
    >
      Card description text goes here.
    </p>
  </div>
</div>
```

### Colored Background Section

```html
<section style="background-color:#f8f9fa">
  <div class="container" style="padding:4rem 0">
    <div class="row">
      <!-- Content -->
    </div>
  </div>
</section>
```

### Call-to-Action Box

```html
<div
  class="text-center bg-primary"
  style="padding:3rem 2rem; border-radius:16px; margin:2rem 0"
>
  <h3
    style="color:#ffffff; font-weight:700; font-size:2rem; margin-bottom:1rem"
  >
    Call to Action
  </h3>
  <p style="color:#f8f9fa; font-size:1.1rem; margin-bottom:1.5rem">
    Supporting text
  </p>
  <div style="color:#ffffff; font-weight:600">
    <i class="fa fa-arrow-right" style="margin-right:0.5rem"></i>
    Action Text
  </div>
</div>
```

### Code Block

```html
<pre
  class="bg-dark"
  style="color:#ffffff; margin:0; padding:1.25rem; border-radius:12px; border:none; white-space:pre; font-family:monospace; font-size:0.85rem; line-height:1.6"
>
def example_function():
    return "Hello, Odoo!"
</pre>
```

### Image with Border

```html
<div class="text-center">
  <img
    src="//apps.odoocdn.com/apps/assets/18.0/MODULE_NAME/screenshot.png"
    alt="Screenshot description"
    class="img-fluid rounded border border-primary"
    style="max-width:100%; display:block; margin:0 auto"
  />
  <p class="text-muted mt-3" style="font-size:1rem">Image caption</p>
</div>
```

### Horizontal Divider

```html
<hr class="my-5 bg-secondary" style="height:2px; border:none; opacity:0.5" />
```

## FontAwesome Icons (Commonly Used)

### Actions

```
fa-check, fa-times, fa-plus, fa-minus, fa-edit, fa-trash
fa-search, fa-filter, fa-download, fa-upload
```

### UI Elements

```
fa-home, fa-cog, fa-user, fa-users, fa-bell, fa-envelope
fa-star, fa-heart, fa-bookmark, fa-flag
```

### Technical

```
fa-code, fa-terminal, fa-database, fa-server, fa-cloud
fa-github, fa-gitlab, fa-git
```

### Business

```
fa-money, fa-credit-card, fa-shopping-cart, fa-chart-line
fa-file, fa-folder, fa-archive, fa-clipboard
```

### Communication

```
fa-comments, fa-comment, fa-phone, fa-mobile
fa-globe, fa-wifi, fa-link
```

### Arrows & Navigation

```
fa-arrow-right, fa-arrow-left, fa-arrow-up, fa-arrow-down
fa-chevron-right, fa-chevron-left, fa-angle-right, fa-angle-left
```

### Status

```
fa-check-circle, fa-times-circle, fa-exclamation-triangle
fa-info-circle, fa-question-circle, fa-lightbulb-o
```

## Image CDN Format

```html
<!-- Format -->
//apps.odoocdn.com/apps/assets/ODOO_VERSION/MODULE_TECHNICAL_NAME/filename.png

<!-- Example -->
//apps.odoocdn.com/apps/assets/18.0/llm_mcp_server/screenshot.png

<!-- With cache-busting parameter (optional) -->
//apps.odoocdn.com/apps/assets/18.0/llm_mcp_server/screenshot.png?9203e76
```

## File Structure

```
module_name/
├── __manifest__.py
├── static/
│   └── description/
│       ├── index.html          # Main landing page (this file)
│       ├── icon.png            # Module icon (128x128)
│       ├── screenshot.png      # Screenshots
│       ├── demo.gif            # Demo animations
│       └── banner.png          # Header images
```

## Testing Checklist

Copy this checklist when creating a landing page:

```
Landing Page Validation Checklist:

HTML Structure:
[ ] File starts with <section>, NOT <!DOCTYPE>
[ ] No <html>, <head>, <body> tags
[ ] Uses Bootstrap 5 container > row > col-* structure

CSS & Styling:
[ ] All colors are hex format (#xxxxxx), no rgba()
[ ] No CSS transitions, transforms, or animations
[ ] No linear gradients
[ ] Box shadows use Bootstrap classes (shadow-sm, etc.)
[ ] Flexbox alignment via Bootstrap classes, NOT inline styles
[ ] Icon centering uses text-center + line-height OR Bootstrap classes

JavaScript:
[ ] No inline JavaScript (onclick, onmouseover, etc.)
[ ] No <script> tags

Content:
[ ] Special characters use HTML entities (&rarr; not →)
[ ] External links are mailto: or displayed as plain text
[ ] All images use Odoo CDN format

Responsive:
[ ] All columns have mobile class (col-12)
[ ] Tested responsive patterns (col-md-*, col-lg-*)
[ ] Cards use h-100 for equal heights in rows

Typography:
[ ] Headings use proper hierarchy (h1, h2, h3)
[ ] Font sizes use rem or px units
[ ] Line heights set for readability

Accessibility:
[ ] Images have descriptive alt text
[ ] Color contrast meets minimum standards
[ ] Links are distinguishable from text

Performance:
[ ] Images optimized for web
[ ] No external CSS/JS dependencies
[ ] Minimal inline styles (prefer Bootstrap classes)
```

## Common Mistakes & Fixes

| Mistake                                 | Problem          | Solution                               |
| --------------------------------------- | ---------------- | -------------------------------------- |
| `style="align-items:center"`            | Gets stripped    | Use `class="align-items-center"`       |
| `style="justify-content:center"`        | Gets stripped    | Use `class="justify-content-center"`   |
| `→` in text                             | Becomes `â`      | Use `&rarr;`                           |
| `<a href="https://github.com">Link</a>` | Becomes `<span>` | Show as `<code>github.com/repo</code>` |
| `rgba(135,90,123,0.1)`                  | Gets stripped    | Convert to hex equivalent `#f5efff`    |
| Missing `col-12`                        | Broken on mobile | Always add `col-12` for mobile         |
| Inline flexbox gap                      | Gets stripped    | Use Bootstrap spacing classes          |

## Resources

- **Main Guide**: `ODOO_APP_STORE_HTML_GUIDE.md` in project root
- **Working Example**: `llm_mcp_server/static/description/index.html`
- **Bootstrap 5 Docs**: getbootstrap.com (for class reference)
- **FontAwesome**: fontawesome.com (for icon names)
