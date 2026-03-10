{
    "name": "LLM Skills",
    "version": "18.0.1.0.1",
    "category": "Technical",
    "summary": "Skill documents for LLM assistants — filesystem-loaded, RAG-retrieved",
    "description": """
        Provides infrastructure for loading versioned skill documents from the
        filesystem into llm.knowledge.collection on Odoo boot/upgrade.

        Skills are markdown files with YAML frontmatter. On boot/upgrade,
        changed files are re-embedded; unchanged files are skipped via SHA-256
        content hash comparison.

        - llm.skill.document: Odoo model that holds skill markdown content
        - llm.skills.loader: scans a directory and syncs skill documents into a collection
        - technical_skill_retriever: @llm_tool that the LLM calls to look up patterns
        - llm.assistant: extended with technical_skills_collection_id
    """,
    "author": "Apexive Solutions LLC / Kajandé",
    "website": "https://github.com/apexive/odoo-llm",
    "license": "LGPL-3",
    "depends": [
        "llm_knowledge",
        "llm_tool",
        "llm_tool_knowledge",
        "llm_assistant",
        "llm_pgvector",
        "llm_openai",
    ],
    "external_dependencies": {
        "python": ["pyyaml"],
    },
    "data": [
        "security/ir.model.access.csv",
        "data/llm_tool_data.xml",
        "data/llm_provider_data.xml",
        "data/llm_store_data.xml",
        "views/llm_skill_document_views.xml",
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
