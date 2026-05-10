{
    "name": "LLM Tool Website",
    "version": "19.0.1.0.0",
    "category": "Productivity/LLM",
    "summary": "31 AI-powered website tools: pages, content, media, menus, "
    "SEO, redirects, visitor analytics, and configuration",
    "description": """
        LLM Tool Website - AI-Powered Website Management for Odoo

        Provides 31 purpose-built website tools for AI assistants and MCP
        servers. Designed for web designers, content managers, and marketing
        teams who use AI daily.

        Pages (6 tools):
        • Find, create, update, publish, clone, and delete website pages
        • Manage page properties: indexing, publish date, header/footer,
          visibility, header overlay/color

        Content (2 tools):
        • Read raw HTML content of any website page
        • Update page HTML content directly

        Media (5 tools):
        • Find media files by name, type, or mimetype
        • Upload images from URL or base64 data
        • Get detailed media info and delete attachments

        Menus (5 tools):
        • Get full menu hierarchy tree
        • Find, create, update, and delete menu items
        • Support for mega menus, page links, and group visibility

        SEO (3 tools):
        • Get and update meta title, description, keywords, and seo_name
        • Audit published pages for incomplete SEO metadata

        Redirects (4 tools):
        • Find, create, update, and delete URL redirect rules
        • Support for permanent (301), temporary (302), rewrite (308),
          and not_found (404) redirect types

        Visitor Analytics (3 tools):
        • Aggregate visitor statistics with top pages
        • Search visitors by partner, country, or connection status
        • Detailed visitor info with page visit history

        Configuration (3 tools):
        • List all websites
        • Get full configuration (languages, social, analytics, CDN,
          robots.txt, custom code, favicon, logo, signup policy)
        • Update website settings

        All tools use Odoo's native methods, respect access controls,
        and follow MCP destructive/read-only hint conventions.
    """,
    "author": "Apexive Solutions LLC",
    "website": "https://github.com/apexive/odoo-llm",
    "license": "LGPL-3",
    "depends": [
        "llm_tool",
        "website",
    ],
    "data": [
        "security/ir.model.access.csv",
    ],
    "images": [
        "static/description/banner.jpeg",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
