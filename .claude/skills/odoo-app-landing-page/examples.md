# Landing Page Examples

## Example 1: Minimal Module Landing Page

Perfect for simple utility modules.

```html
<!-- Hero Section -->
<section style="padding:4rem 0 3rem">
  <div class="container">
    <div class="text-center" style="max-width:800px; margin:0 auto">
      <h1
        style="font-size:3rem; font-weight:800; color:#212529; margin-bottom:1.5rem; line-height:1.2"
      >
        Module Name
      </h1>
      <p
        style="font-size:1.25rem; color:#6c757d; margin-bottom:2rem; line-height:1.6"
      >
        Brief description of what this module does in one or two sentences.
      </p>
    </div>
  </div>
</section>

<div class="container my-5">
  <!-- Features Section -->
  <section class="mb-5">
    <h2
      class="text-center mb-4"
      style="font-size:2.5rem; font-weight:700; color:#71639e"
    >
      Key Features
    </h2>

    <div class="row g-4">
      <div class="col-md-4 col-12">
        <div class="card h-100 border-0 shadow-sm" style="border-radius:16px">
          <div class="card-body p-4 text-center">
            <div
              class="bg-light d-flex align-items-center justify-content-center"
              style="width:64px; height:64px; border-radius:12px; margin:0 auto 1.5rem"
            >
              <i class="fa fa-check" style="font-size:32px; color:#71639e"></i>
            </div>
            <h3
              style="font-size:1.25rem; font-weight:700; color:#212529; margin-bottom:1rem"
            >
              Feature One
            </h3>
            <p
              style="color:#6c757d; font-size:0.95rem; line-height:1.7; margin-bottom:0"
            >
              Description of the first key feature.
            </p>
          </div>
        </div>
      </div>

      <div class="col-md-4 col-12">
        <div class="card h-100 border-0 shadow-sm" style="border-radius:16px">
          <div class="card-body p-4 text-center">
            <div
              class="bg-light d-flex align-items-center justify-content-center"
              style="width:64px; height:64px; border-radius:12px; margin:0 auto 1.5rem"
            >
              <i class="fa fa-bolt" style="font-size:32px; color:#71639e"></i>
            </div>
            <h3
              style="font-size:1.25rem; font-weight:700; color:#212529; margin-bottom:1rem"
            >
              Feature Two
            </h3>
            <p
              style="color:#6c757d; font-size:0.95rem; line-height:1.7; margin-bottom:0"
            >
              Description of the second key feature.
            </p>
          </div>
        </div>
      </div>

      <div class="col-md-4 col-12">
        <div class="card h-100 border-0 shadow-sm" style="border-radius:16px">
          <div class="card-body p-4 text-center">
            <div
              class="bg-light d-flex align-items-center justify-content-center"
              style="width:64px; height:64px; border-radius:12px; margin:0 auto 1.5rem"
            >
              <i class="fa fa-shield" style="font-size:32px; color:#71639e"></i>
            </div>
            <h3
              style="font-size:1.25rem; font-weight:700; color:#212529; margin-bottom:1rem"
            >
              Feature Three
            </h3>
            <p
              style="color:#6c757d; font-size:0.95rem; line-height:1.7; margin-bottom:0"
            >
              Description of the third key feature.
            </p>
          </div>
        </div>
      </div>
    </div>
  </section>

  <hr class="my-5 bg-secondary" style="height:2px; border:none; opacity:0.5" />

  <!-- Support Section -->
  <section class="mb-5">
    <h2
      class="text-center mb-4"
      style="font-size:2.5rem; font-weight:700; color:#71639e"
    >
      Support
    </h2>
    <div class="row justify-content-center">
      <div class="col-md-6 col-12">
        <div class="card border-0 shadow-sm" style="border-radius:16px">
          <div class="card-body p-4 text-center">
            <p style="color:#495057; margin-bottom:1.5rem">
              Need help? We're here for you.
            </p>
            <a
              href="mailto:support@example.com"
              class="btn btn-primary"
              style="background-color:#71639e; border:none; border-radius:8px; padding:0.75rem 2rem"
            >
              Contact Support
            </a>
          </div>
        </div>
      </div>
    </div>
  </section>
</div>

<!-- Footer -->
<footer
  class="bg-primary"
  style="padding:3rem 2rem; border-radius:16px; margin:2rem 1rem"
>
  <div class="container">
    <div class="text-center">
      <h4
        style="font-weight:700; color:#ffffff; font-size:1.5rem; margin-bottom:0.75rem"
      >
        Module Name
      </h4>
      <p style="color:#f8f9fa; font-size:1rem; margin-bottom:1rem">
        Brief tagline
      </p>
      <p style="color:#e9d5ff; margin-bottom:0.25rem">
        Developed by <strong style="color:#ffffff">Your Company</strong>
      </p>
      <p style="color:#e0d4ec; font-size:0.9rem; margin-bottom:0">
        Licensed under AGPL-3 &bull; &copy; 2025
      </p>
    </div>
  </div>
</footer>
```

## Example 2: Technical/Developer-Focused Module

For modules that require code integration or API usage.

```html
<!-- Hero Section -->
<section style="padding:4rem 0 3rem">
  <div class="container">
    <div class="text-center" style="max-width:800px; margin:0 auto">
      <div
        style="display:inline-flex; padding:0.5rem 1.25rem; border-radius:50px; margin-bottom:2rem"
      >
        <i
          class="fa fa-code"
          style="color:#71639e; font-size:1.25rem; margin-right:0.5rem"
        ></i>
        <span style="color:#71639e; font-weight:600; font-size:0.9rem"
          >Developer Tool</span
        >
      </div>

      <h1
        style="font-size:3rem; font-weight:800; color:#212529; margin-bottom:1.5rem; line-height:1.2"
      >
        Powerful Integration<br />
        <span style="color:#71639e">Made Simple</span>
      </h1>

      <p
        style="font-size:1.25rem; color:#6c757d; margin-bottom:2rem; line-height:1.6"
      >
        Connect your Odoo instance to external services with just a few lines of
        code.
      </p>
    </div>
  </div>
</section>

<div class="container my-5">
  <!-- Quick Start Section -->
  <section class="mb-5">
    <h2
      class="text-center mb-4"
      style="font-size:2.5rem; font-weight:700; color:#71639e"
    >
      Quick Start
    </h2>

    <div class="row justify-content-center">
      <div class="col-lg-8 col-12">
        <div class="card border-0 shadow-sm" style="border-radius:16px">
          <div class="card-body p-4">
            <h3
              style="font-size:1.5rem; font-weight:700; color:#212529; margin-bottom:1rem"
            >
              Installation
            </h3>
            <p style="color:#495057; margin-bottom:1rem">
              Install the module from Apps menu:
            </p>
            <ol style="color:#495057; margin-bottom:1.5rem">
              <li>Navigate to Apps</li>
              <li>Search for "Module Name"</li>
              <li>Click Install</li>
            </ol>

            <h3
              style="font-size:1.5rem; font-weight:700; color:#212529; margin-bottom:1rem"
            >
              Basic Usage
            </h3>
            <p style="color:#495057; margin-bottom:1rem">
              Add this decorator to any model method:
            </p>
            <pre
              class="bg-dark"
              style="color:#ffffff; margin:0; padding:1.25rem; border-radius:12px; border:none; white-space:pre; font-family:monospace; font-size:0.85rem; line-height:1.6"
            >
from odoo import models
from odoo.addons.module_name.decorators import my_decorator

class MyModel(models.Model):
    _inherit = 'res.partner'

    @my_decorator
    def custom_method(self):
        return "Hello, World!"</pre
            >
          </div>
        </div>
      </div>
    </div>
  </section>

  <hr class="my-5 bg-secondary" style="height:2px; border:none; opacity:0.5" />

  <!-- Features Section -->
  <section class="mb-5">
    <h2
      class="text-center mb-4"
      style="font-size:2.5rem; font-weight:700; color:#71639e"
    >
      Developer Features
    </h2>

    <div class="row g-4">
      <div class="col-md-6 col-12">
        <div class="card h-100 border-0 shadow-sm" style="border-radius:16px">
          <div class="card-body p-4">
            <div
              class="bg-light d-flex align-items-center justify-content-center"
              style="width:56px; height:56px; border-radius:12px; margin-bottom:1.5rem"
            >
              <i class="fa fa-code" style="font-size:28px; color:#71639e"></i>
            </div>
            <h3
              style="font-size:1.25rem; font-weight:700; color:#212529; margin-bottom:1rem"
            >
              Simple API
            </h3>
            <p
              style="color:#6c757d; font-size:0.95rem; line-height:1.7; margin-bottom:0"
            >
              Clean, intuitive API that follows Odoo conventions. No learning
              curve.
            </p>
          </div>
        </div>
      </div>

      <div class="col-md-6 col-12">
        <div class="card h-100 border-0 shadow-sm" style="border-radius:16px">
          <div class="card-body p-4">
            <div
              class="bg-light d-flex align-items-center justify-content-center"
              style="width:56px; height:56px; border-radius:12px; margin-bottom:1.5rem"
            >
              <i class="fa fa-book" style="font-size:28px; color:#71639e"></i>
            </div>
            <h3
              style="font-size:1.25rem; font-weight:700; color:#212529; margin-bottom:1rem"
            >
              Well Documented
            </h3>
            <p
              style="color:#6c757d; font-size:0.95rem; line-height:1.7; margin-bottom:0"
            >
              Comprehensive documentation with examples and best practices.
            </p>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Documentation Section -->
  <section class="mb-5">
    <div
      class="text-center bg-light"
      style="padding:3rem 2rem; border-radius:16px"
    >
      <h3
        style="color:#212529; font-weight:700; font-size:2rem; margin-bottom:1rem"
      >
        Full Documentation
      </h3>
      <p style="color:#495057; font-size:1.1rem; margin-bottom:1.5rem">
        Complete API reference and integration guides
      </p>
      <p style="color:#71639e; font-weight:600; margin-bottom:0">
        <code
          style="background-color:#fff; padding:0.5rem 1rem; border-radius:8px"
        >
          github.com/yourorg/module-name
        </code>
      </p>
    </div>
  </section>
</div>
```

## Example 3: Business/End-User Module

For modules targeting business users, not developers.

```html
<!-- Hero Section -->
<section style="padding:4rem 0 3rem; background-color:#f8f9fa">
  <div class="container">
    <div class="text-center" style="max-width:900px; margin:0 auto">
      <h1
        style="font-size:3.5rem; font-weight:800; color:#212529; margin-bottom:1.5rem; line-height:1.2"
      >
        Simplify Your Workflow
      </h1>

      <p
        style="font-size:1.4rem; color:#495057; margin-bottom:2.5rem; line-height:1.6"
      >
        Automate repetitive tasks and save hours every week with intelligent
        automation.
      </p>

      <div
        class="d-flex justify-content-center flex-wrap"
        style="margin-bottom:2rem"
      >
        <div
          class="bg-white d-flex align-items-center"
          style="padding:0.75rem 1.5rem; border-radius:12px; margin:0.5rem"
        >
          <i
            class="fa fa-check-circle"
            style="color:#28a745; font-size:1.25rem; margin-right:0.5rem"
          ></i>
          <span style="color:#155724; font-weight:600">Easy Setup</span>
        </div>
        <div
          class="bg-white d-flex align-items-center"
          style="padding:0.75rem 1.5rem; border-radius:12px; margin:0.5rem"
        >
          <i
            class="fa fa-users"
            style="color:#17a2b8; font-size:1.25rem; margin-right:0.5rem"
          ></i>
          <span style="color:#0c5460; font-weight:600">Team Ready</span>
        </div>
        <div
          class="bg-white d-flex align-items-center"
          style="padding:0.75rem 1.5rem; border-radius:12px; margin:0.5rem"
        >
          <i
            class="fa fa-rocket"
            style="color:#71639e; font-size:1.25rem; margin-right:0.5rem"
          ></i>
          <span style="color:#5b4c7d; font-weight:600">Instant Results</span>
        </div>
      </div>
    </div>
  </div>
</section>

<div class="container my-5">
  <!-- Benefits Section -->
  <section class="mb-5">
    <h2
      class="text-center mb-3"
      style="font-size:2.5rem; font-weight:700; color:#71639e"
    >
      Why Teams Love This
    </h2>
    <p class="text-center mb-5" style="font-size:1.2rem; color:#6c757d">
      Save time and reduce errors with smart automation
    </p>

    <div class="row g-4">
      <div class="col-md-4 col-12">
        <div
          class="card h-100 text-center border-0 shadow-sm"
          style="border-radius:16px; background-color:#f5efff"
        >
          <div class="card-body p-4">
            <div
              class="d-flex align-items-center justify-content-center"
              style="width:64px; height:64px; border-radius:50%; background-color:#71639e; margin:0 auto 1.5rem"
            >
              <i
                class="fa fa-clock-o"
                style="font-size:32px; color:#ffffff"
              ></i>
            </div>
            <h3
              style="font-size:1.25rem; font-weight:700; color:#5b4c7d; margin-bottom:1rem"
            >
              Save Hours Weekly
            </h3>
            <p style="color:#5b4c7d; margin-bottom:0">
              Automate repetitive tasks that waste your team's valuable time.
            </p>
          </div>
        </div>
      </div>

      <div class="col-md-4 col-12">
        <div
          class="card h-100 text-center border-0 shadow-sm"
          style="border-radius:16px; background-color:#f5efff"
        >
          <div class="card-body p-4">
            <div
              class="d-flex align-items-center justify-content-center"
              style="width:64px; height:64px; border-radius:50%; background-color:#71639e; margin:0 auto 1.5rem"
            >
              <i
                class="fa fa-check-square-o"
                style="font-size:32px; color:#ffffff"
              ></i>
            </div>
            <h3
              style="font-size:1.25rem; font-weight:700; color:#5b4c7d; margin-bottom:1rem"
            >
              Reduce Mistakes
            </h3>
            <p style="color:#5b4c7d; margin-bottom:0">
              Eliminate human error with consistent, automated processes.
            </p>
          </div>
        </div>
      </div>

      <div class="col-md-4 col-12">
        <div
          class="card h-100 text-center border-0 shadow-sm"
          style="border-radius:16px; background-color:#f5efff"
        >
          <div class="card-body p-4">
            <div
              class="d-flex align-items-center justify-content-center"
              style="width:64px; height:64px; border-radius:50%; background-color:#71639e; margin:0 auto 1.5rem"
            >
              <i
                class="fa fa-smile-o"
                style="font-size:32px; color:#ffffff"
              ></i>
            </div>
            <h3
              style="font-size:1.25rem; font-weight:700; color:#5b4c7d; margin-bottom:1rem"
            >
              Happier Team
            </h3>
            <p style="color:#5b4c7d; margin-bottom:0">
              Let your team focus on meaningful work, not tedious data entry.
            </p>
          </div>
        </div>
      </div>
    </div>
  </section>

  <hr class="my-5 bg-secondary" style="height:2px; border:none; opacity:0.5" />

  <!-- How It Works Section -->
  <section class="mb-5">
    <h2
      class="text-center mb-5"
      style="font-size:2.5rem; font-weight:700; color:#71639e"
    >
      How It Works
    </h2>

    <div class="row g-4">
      <div class="col-md-4 col-12">
        <div class="text-center">
          <div
            class="d-flex align-items-center justify-content-center"
            style="width:80px; height:80px; border-radius:50%; background-color:#71639e; margin:0 auto 1.5rem"
          >
            <span style="color:white; font-size:2rem; font-weight:700">1</span>
          </div>
          <h3
            style="font-size:1.25rem; font-weight:700; color:#212529; margin-bottom:1rem"
          >
            Install &amp; Configure
          </h3>
          <p style="color:#6c757d; font-size:1rem; line-height:1.6">
            Simple 5-minute setup. No technical knowledge required.
          </p>
        </div>
      </div>

      <div class="col-md-4 col-12">
        <div class="text-center">
          <div
            class="d-flex align-items-center justify-content-center"
            style="width:80px; height:80px; border-radius:50%; background-color:#71639e; margin:0 auto 1.5rem"
          >
            <span style="color:white; font-size:2rem; font-weight:700">2</span>
          </div>
          <h3
            style="font-size:1.25rem; font-weight:700; color:#212529; margin-bottom:1rem"
          >
            Set Your Rules
          </h3>
          <p style="color:#6c757d; font-size:1rem; line-height:1.6">
            Define when and how automation should trigger.
          </p>
        </div>
      </div>

      <div class="col-md-4 col-12">
        <div class="text-center">
          <div
            class="d-flex align-items-center justify-content-center"
            style="width:80px; height:80px; border-radius:50%; background-color:#71639e; margin:0 auto 1.5rem"
          >
            <span style="color:white; font-size:2rem; font-weight:700">3</span>
          </div>
          <h3
            style="font-size:1.25rem; font-weight:700; color:#212529; margin-bottom:1rem"
          >
            Relax &amp; Monitor
          </h3>
          <p style="color:#6c757d; font-size:1rem; line-height:1.6">
            Let the system work. Track results in the dashboard.
          </p>
        </div>
      </div>
    </div>
  </section>

  <!-- CTA Section -->
  <section class="mb-5">
    <div
      class="text-center bg-primary"
      style="padding:3rem 2rem; border-radius:16px"
    >
      <h3
        style="color:#ffffff; font-weight:700; font-size:2rem; margin-bottom:1rem"
      >
        Ready to Save Time?
      </h3>
      <p style="color:#f8f9fa; font-size:1.1rem; margin-bottom:1.5rem">
        Join hundreds of teams already using this module
      </p>
      <div
        class="bg-white"
        style="padding:1rem 2rem; border-radius:12px; display:inline-block"
      >
        <span style="color:#71639e; font-size:1.1rem; font-weight:600">
          Install Now from Odoo Apps
        </span>
      </div>
    </div>
  </section>
</div>
```

## Example 4: Integration/Connector Module

For modules that connect Odoo to external services.

```html
<!-- Hero Section -->
<section style="padding:4rem 0 3rem">
  <div class="container">
    <div class="text-center" style="max-width:800px; margin:0 auto">
      <h1
        style="font-size:3rem; font-weight:800; color:#212529; margin-bottom:1.5rem"
      >
        Connect Odoo to <span style="color:#71639e">External Service</span>
      </h1>

      <p
        style="font-size:1.25rem; color:#6c757d; margin-bottom:2rem; line-height:1.6"
      >
        Seamless two-way sync between Odoo and External Service. Real-time
        updates, zero manual work.
      </p>
    </div>
  </div>
</section>

<div class="container my-5">
  <!-- What You Can Do Section -->
  <section class="mb-5">
    <h2
      class="text-center mb-4"
      style="font-size:2.5rem; font-weight:700; color:#71639e"
    >
      What You Can Sync
    </h2>

    <div class="row g-4">
      <div class="col-md-6 col-12">
        <div
          class="card border-0 shadow-sm"
          style="padding:2rem; border-radius:16px"
        >
          <div
            class="bg-light d-flex align-items-center justify-content-center"
            style="width:56px; height:56px; border-radius:12px; margin-bottom:1.5rem"
          >
            <i class="fa fa-users" style="font-size:28px; color:#71639e"></i>
          </div>
          <h3
            style="font-size:1.25rem; font-weight:700; color:#212529; margin-bottom:0.75rem"
          >
            Contacts &amp; Customers
          </h3>
          <p style="color:#6c757d; margin-bottom:0">
            Automatically sync customer data between Odoo and External Service.
          </p>
        </div>
      </div>

      <div class="col-md-6 col-12">
        <div
          class="card border-0 shadow-sm"
          style="padding:2rem; border-radius:16px"
        >
          <div
            class="bg-light d-flex align-items-center justify-content-center"
            style="width:56px; height:56px; border-radius:12px; margin-bottom:1.5rem"
          >
            <i
              class="fa fa-shopping-cart"
              style="font-size:28px; color:#71639e"
            ></i>
          </div>
          <h3
            style="font-size:1.25rem; font-weight:700; color:#212529; margin-bottom:0.75rem"
          >
            Orders &amp; Invoices
          </h3>
          <p style="color:#6c757d; margin-bottom:0">
            Keep sales data in sync. Orders flow automatically.
          </p>
        </div>
      </div>

      <div class="col-md-6 col-12">
        <div
          class="card border-0 shadow-sm"
          style="padding:2rem; border-radius:16px"
        >
          <div
            class="bg-light d-flex align-items-center justify-content-center"
            style="width:56px; height:56px; border-radius:12px; margin-bottom:1.5rem"
          >
            <i class="fa fa-cube" style="font-size:28px; color:#71639e"></i>
          </div>
          <h3
            style="font-size:1.25rem; font-weight:700; color:#212529; margin-bottom:0.75rem"
          >
            Products &amp; Inventory
          </h3>
          <p style="color:#6c757d; margin-bottom:0">
            Real-time inventory updates across platforms.
          </p>
        </div>
      </div>

      <div class="col-md-6 col-12">
        <div
          class="card border-0 shadow-sm"
          style="padding:2rem; border-radius:16px"
        >
          <div
            class="bg-light d-flex align-items-center justify-content-center"
            style="width:56px; height:56px; border-radius:12px; margin-bottom:1.5rem"
          >
            <i
              class="fa fa-file-text-o"
              style="font-size:28px; color:#71639e"
            ></i>
          </div>
          <h3
            style="font-size:1.25rem; font-weight:700; color:#212529; margin-bottom:0.75rem"
          >
            Documents &amp; Files
          </h3>
          <p style="color:#6c757d; margin-bottom:0">
            Attach files from External Service to Odoo records.
          </p>
        </div>
      </div>
    </div>
  </section>

  <hr class="my-5 bg-secondary" style="height:2px; border:none; opacity:0.5" />

  <!-- Setup Section -->
  <section class="mb-5">
    <h2
      class="text-center mb-4"
      style="font-size:2.5rem; font-weight:700; color:#71639e"
    >
      5-Minute Setup
    </h2>

    <div class="row justify-content-center">
      <div class="col-lg-8 col-12">
        <div class="card border-0 shadow-sm" style="border-radius:16px">
          <div class="card-body p-4">
            <div class="mb-4">
              <div class="d-flex align-items-start">
                <div
                  class="text-center"
                  style="min-width:40px; height:40px; line-height:40px; border-radius:50%; background-color:#71639e; color:#fff; font-weight:700; margin-right:1rem"
                >
                  1
                </div>
                <div>
                  <h4
                    style="font-weight:700; color:#212529; margin-bottom:0.5rem"
                  >
                    Install Module
                  </h4>
                  <p style="color:#6c757d; margin-bottom:0">
                    Search for module in Odoo Apps and click Install
                  </p>
                </div>
              </div>
            </div>

            <div class="mb-4">
              <div class="d-flex align-items-start">
                <div
                  class="text-center"
                  style="min-width:40px; height:40px; line-height:40px; border-radius:50%; background-color:#71639e; color:#fff; font-weight:700; margin-right:1rem"
                >
                  2
                </div>
                <div>
                  <h4
                    style="font-weight:700; color:#212529; margin-bottom:0.5rem"
                  >
                    Connect Account
                  </h4>
                  <p style="color:#6c757d; margin-bottom:0">
                    Add your External Service API credentials in Settings
                  </p>
                </div>
              </div>
            </div>

            <div class="mb-0">
              <div class="d-flex align-items-start">
                <div
                  class="text-center"
                  style="min-width:40px; height:40px; line-height:40px; border-radius:50%; background-color:#71639e; color:#fff; font-weight:700; margin-right:1rem"
                >
                  3
                </div>
                <div>
                  <h4
                    style="font-weight:700; color:#212529; margin-bottom:0.5rem"
                  >
                    Start Syncing
                  </h4>
                  <p style="color:#6c757d; margin-bottom:0">
                    Click "Sync Now" and watch your data flow automatically
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</div>
```

## Tips for Using These Examples

1. **Copy the structure, customize the content**: These are templates, not final products
2. **Adjust colors**: You can use any hex color from the safe palette
3. **Change icons**: Replace `fa-check` with any FontAwesome icon
4. **Add/remove sections**: Mix and match sections based on your module's needs
5. **Keep it focused**: Don't include every section - choose what's relevant
6. **Test responsiveness**: View on mobile to ensure proper col-12 usage

## Finding the Right Icon

Visit fontawesome.com and search for relevant icons. Common choices:

- **Features**: fa-check, fa-star, fa-heart, fa-bolt
- **Technical**: fa-code, fa-terminal, fa-database, fa-cog
- **Business**: fa-money, fa-chart-line, fa-briefcase
- **Communication**: fa-comments, fa-envelope, fa-phone
- **Users**: fa-user, fa-users, fa-user-circle
- **Actions**: fa-plus, fa-edit, fa-trash, fa-download
