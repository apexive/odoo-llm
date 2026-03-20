{
    "name": "LLM Skills",
    "version": "18.0.2.0.0",
    "category": "Technical",
    "summary": "Skill documents for LLM assistants — description-indexed, progressive disclosure",
    "description": """
        Filesystem-loaded skill documents for LLM assistants.

        Skills are SKILL.md files in per-skill directories with YAML frontmatter.
        On boot/upgrade, only the description field is embedded (one vector per skill).
        The LLM uses a two-stage approach: odoo_skill_searcher returns a short
        manifest (name + description), then odoo_skill_reader loads full content
        on demand.

        - llm.skill: holds skill name, description, and full content body
        - llm.skills.loader: scans a directory and syncs skills into a collection
        - odoo_skill_searcher: @llm_tool — returns top-4 skill manifest for a query
        - odoo_skill_reader: @llm_tool — loads full skill content by name
        - llm.assistant: extended with skills_collection_id
    """,
    "author": "Apexive Solutions LLC / Kajandé",
    "website": "https://github.com/apexive/odoo-llm",
    "license": "LGPL-3",
    "depends": [
        "llm_knowledge",
        "llm_tool",
        "llm_assistant",
        "llm_pgvector",
        "llm_ollama",
        "llm_anthropic",
    ],
    "external_dependencies": {
        "python": ["pyyaml"],
    },
    "data": [
        "security/ir.model.access.csv",
        "data/llm_tool_data.xml",
        "data/llm_provider_data.xml",
        "data/llm_store_data.xml",
        "data/llm_loader_data.xml",
        "data/llm_admin_assistant_data.xml",
        "views/llm_skill_views.xml",
        "views/llm_skills_loader_views.xml",
        "views/llm_assistant_views.xml",
        "views/menu.xml",
    ],
    "images": [
        "static/description/banner.jpeg",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
