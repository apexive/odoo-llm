---
name: odoo-app-landing-page
description: Create or update index.html landing pages for Odoo modules following App Store restrictions and best practices
allowed-tools: Read, Write, Edit, Grep, Glob
---

# Odoo App Store Landing Page Creator

When the user asks to create or update an `index.html` file for an Odoo module's landing page, follow these instructions to ensure compliance with Odoo App Store sanitization rules.

## Overview

Odoo App Store has strict HTML/CSS sanitization that strips many common patterns. This skill helps you create landing pages that survive sanitization and look professional.

## Key Resources

1. **Reference Guide**: `ODOO_APP_STORE_HTML_GUIDE.md` - Complete documentation of safe/unsafe patterns
2. **Working Example**: `llm_mcp_server/static/description/index.html` - Production-ready example

## CRITICAL Rules (Must Follow)

### ❌ NEVER USE (Will Be Stripped)

1. **NO DOCTYPE or full HTML structure**

   - Don't include `<!DOCTYPE>`, `<html>`, `<head>`, `<body>` tags
   - Start directly with `<section>` tags

2. **NO inline flexbox alignment properties**

   ```html
   <!-- ❌ BAD - Will be stripped -->
   <div style="display:flex; align-items:center; justify-content:center">
     <!-- ✅ GOOD - Use Bootstrap classes -->
     <div class="d-flex align-items-center justify-content-center"></div>
   </div>
   ```

3. **NO rgba() colors**

   ```html
   <!-- ❌ BAD -->
   <div style="background-color:rgba(135,90,123,0.1)">
     <!-- ✅ GOOD - Use hex -->
     <div style="background-color:#f5efff"></div>
   </div>
   ```

4. **NO transitions, transforms, or animations**

   - These CSS properties are completely stripped

5. **NO inline JavaScript**

   - No `onclick`, `onmouseover`, or any event handlers

6. **NO linear gradients**

   - Use solid colors only

7. **NO external links (mostly)**

   ```html
   <!-- ❌ BAD - Becomes <span> -->
   <a href="https://github.com/yourorg">GitHub</a>

   <!-- ✅ GOOD - Display as text -->
   <code>github.com/yourorg/repo</code>

   <!-- ✅ GOOD - mailto works -->
   <a href="mailto:support@example.com">Contact</a>
   ```

8. **NO unicode special characters**

   ```html
   <!-- ❌ BAD - Becomes garbled (→ becomes â) -->
   Preferences → API Keys

   <!-- ✅ GOOD - Use HTML entities -->
   Preferences &rarr; API Keys
   ```

### ✅ ALWAYS USE (Safe Patterns)

1. **Bootstrap 5 grid system**

   - `container`, `row`, `col-md-*`, `col-lg-*`, `col-12`

2. **Bootstrap utility classes**

   - `d-flex`, `align-items-center`, `justify-content-center`
   - `p-4`, `mb-5`, `mt-3`, `mx-auto`
   - `text-center`, `shadow-sm`, `h-100`

3. **Hex colors only**

   - `#875A7B` (Odoo purple), `#f8f9fa`, `#333`, `#fff`

4. **Inline styles for**

   - `color`, `background-color`, `font-size`, `font-weight`
   - `padding`, `margin`, `border-radius`, `border`
   - `line-height`, `text-align`, `width`, `height`

5. **Icon centering alternatives**

   ```html
   <!-- Method 1: text-center + line-height -->
   <div
     class="text-center"
     style="width:64px; height:64px; line-height:64px; border-radius:50%; background-color:#875A7B"
   >
     <i
       class="fa fa-icon"
       style="color:#fff; font-size:32px; vertical-align:middle"
     ></i>
   </div>

   <!-- Method 2: Bootstrap flex classes -->
   <div
     class="d-flex align-items-center justify-content-center"
     style="width:64px; height:64px; border-radius:50%; background-color:#875A7B"
   >
     <i class="fa fa-icon" style="color:#fff; font-size:32px"></i>
   </div>
   ```

6. **HTML entities for special characters**
   - `&rarr;` (→), `&larr;` (←), `&mdash;` (—), `&copy;` (©), `&bull;` (•)

## Step-by-Step Process

### 1. Gather Module Information

Ask the user (if not already provided):

- Module name and technical name
- Brief description (1-2 sentences)
- Key features (3-6 main features)
- Target use cases or pain points it solves
- Any screenshots or demo images
- Support contact (email)

### 2. Read the Reference Files

**ALWAYS** read these files before starting:

```bash
# Read the comprehensive guide
Read ODOO_APP_STORE_HTML_GUIDE.md

# Read the working example
Read llm_mcp_server/static/description/index.html
```

### 3. Structure the Landing Page

Use this proven structure:

```
1. Hero Section
   - Eye-catching title
   - Brief description
   - Key value propositions (badges/pills)

2. What Is It Section
   - Explain the concept/technology
   - Why it matters
   - Benefits

3. Demo Section (if available)
   - Screenshot or GIF
   - Caption

4. Features Section
   - 4-6 feature cards
   - Icons + descriptions

5. Use Cases Section
   - Real-world examples
   - Natural language operation examples

6. Setup Instructions (if applicable)
   - Step-by-step installation
   - Configuration examples

7. Technical Features (for developers)
   - Code examples
   - Integration points

8. Security/Enterprise Features
   - Access control
   - Compliance
   - Permissions

9. Related Modules
   - Ecosystem integration
   - Cross-sell opportunities

10. Support/Documentation
    - Links to docs (as plain text or code)
    - Contact email (mailto)

11. Footer
    - Company info
    - License
    - Contact links
```

### 4. Apply Color Palette

Use these safe hex colors:

**Primary Colors:**

- Odoo Purple: `#875A7B` or `#71639e` (from example)
- Dark text: `#212529`, `#333`, `#495057`
- Medium gray: `#6c757d`, `#666`
- Light gray: `#868e96`

**Backgrounds:**

- Very light: `#f8f9fa`
- Light purple tint: `#f5efff`, `#f7f2fa`
- White: `#fff` or `#ffffff`

**Accents:**

- Success green: `#28a745`, `#155724`
- Info blue: `#17a2b8`, `#0c5460`
- Warning: `#ffc107`
- Primary blue: `#007bff` (for buttons)

### 5. Responsive Design

**ALWAYS** include responsive column classes:

```html
<!-- 3 columns on desktop, 1 on mobile -->
<div class="col-md-4 col-12 mb-4">
  <!-- 4 columns on desktop, 2 on tablet, 1 on mobile -->
  <div class="col-md-3 col-sm-6 col-12 mb-4">
    <!-- 6 on large, 4 on medium, 2 on small -->
    <div class="col-lg-2 col-md-4 col-6 mb-4"></div>
  </div>
</div>
```

### 6. Card Components Pattern

```html
<div class="col-md-4 col-12 mb-4">
  <div class="card h-100 border-0 shadow-sm" style="border-radius:16px">
    <div class="card-body p-4">
      <div
        class="bg-light d-flex align-items-center justify-content-center"
        style="width:56px; height:56px; border-radius:12px; margin-bottom:1.5rem"
      >
        <i class="fa fa-icon-name" style="font-size:28px; color:#71639e"></i>
      </div>
      <h3
        style="font-size:1.25rem; font-weight:700; color:#212529; margin-bottom:1rem"
      >
        Feature Title
      </h3>
      <p
        style="color:#6c757d; font-size:0.95rem; line-height:1.7; margin-bottom:0"
      >
        Feature description text
      </p>
    </div>
  </div>
</div>
```

### 7. Code Examples Pattern

```html
<pre
  class="bg-dark"
  style="color:#ffffff; margin:0; padding:1.25rem; border-radius:12px; border:none; white-space:pre; font-family:monospace; font-size:0.85rem; line-height:1.6"
>
# Your code here
def example():
    pass
</pre>
```

### 8. Validation Checklist

Before completing, verify:

- [ ] No DOCTYPE, html, head, body tags
- [ ] All colors are hex format, no rgba()
- [ ] No CSS transitions, transforms, or animations
- [ ] No inline JavaScript handlers
- [ ] No inline flexbox alignment properties (use Bootstrap classes)
- [ ] Using Bootstrap 5 grid (container, row, col-\*)
- [ ] All sections have responsive columns
- [ ] Icon centering uses text-center + line-height OR Bootstrap flex classes
- [ ] Special characters use HTML entities (&rarr; not →)
- [ ] External links are mailto: or plain text
- [ ] All images use Odoo CDN format: `//apps.odoocdn.com/apps/assets/18.0/MODULE_NAME/image.png`

### 9. File Location

Landing pages go in:

```
MODULE_NAME/static/description/index.html
```

### 10. Image References

If the module has images:

```html
<img
  src="//apps.odoocdn.com/apps/assets/18.0/MODULE_TECHNICAL_NAME/screenshot.png"
  alt="Descriptive alt text"
  class="img-fluid rounded"
  style="max-width:100%"
/>
```

## Common Patterns Library

### Hero Section

```html
<section style="padding:4rem 0 3rem">
  <div class="container">
    <div class="text-center" style="max-width:800px; margin:0 auto">
      <h1
        style="font-size:3rem; font-weight:800; color:#212529; margin-bottom:1.5rem; line-height:1.2"
      >
        Your Module Title
      </h1>
      <p
        style="font-size:1.25rem; color:#6c757d; margin-bottom:2rem; line-height:1.6"
      >
        Brief compelling description
      </p>
    </div>
  </div>
</section>
```

### Section Divider

```html
<hr class="my-5 bg-secondary" style="height:2px; border:none; opacity:0.5" />
```

### Feature Grid

```html
<div class="row g-4">
  <div class="col-md-4 col-12">
    <!-- Feature card -->
  </div>
  <div class="col-md-4 col-12">
    <!-- Feature card -->
  </div>
  <div class="col-md-4 col-12">
    <!-- Feature card -->
  </div>
</div>
```

### Call-to-Action Box

```html
<div
  class="text-center mb-5 bg-primary"
  style="padding:3rem 2rem; border-radius:16px"
>
  <h3
    style="color:#ffffff; font-weight:700; font-size:2rem; margin-bottom:1rem"
  >
    Call to Action Title
  </h3>
  <p style="color:#f8f9fa; font-size:1.1rem; margin-bottom:0">
    Supporting text
  </p>
</div>
```

## Tips for Success

1. **Start with the example**: Copy structure from `llm_mcp_server/static/description/index.html`
2. **Read the guide**: Reference `ODOO_APP_STORE_HTML_GUIDE.md` for edge cases
3. **Use Bootstrap classes for layout**: Especially for flexbox (d-flex, align-items-center)
4. **Use inline styles for aesthetics**: Colors, fonts, spacing
5. **Think mobile-first**: Always include col-12 for mobile responsiveness
6. **Keep it simple**: Less is more - avoid complex layouts
7. **Test special characters**: Convert all unicode to HTML entities
8. **Avoid external links**: Display URLs as text in `<code>` tags

## When to Use This Skill

- User asks to "create landing page for [module]"
- User asks to "update index.html for [module]"
- User asks to "improve module description page"
- User mentions "Odoo App Store" and "HTML"
- User asks about "module marketing page"

## What NOT to Do

- Don't create generic landing pages - always customize for the specific module
- Don't copy-paste without adapting to the module's purpose
- Don't skip the validation checklist
- Don't use patterns not documented in the guide
- Don't assume features - ask the user if unclear

## Final Notes

The Odoo App Store sanitizer is aggressive. When in doubt:

1. Check the guide (`ODOO_APP_STORE_HTML_GUIDE.md`)
2. Look at the working example (`llm_mcp_server/static/description/index.html`)
3. Use Bootstrap classes instead of inline styles for layout
4. Keep it simple and semantic

Remember: **Bootstrap classes are safer than inline styles** for flexbox and layout properties!
