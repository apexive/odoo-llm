{
    "name": "LLM Tool MIS Builder",
    "version": "19.0.1.0.0",
    "category": "Productivity/LLM",
    "summary": "44 AI-powered tools for MIS Builder: create KPIs, configure periods, "
    "compute reports, drill down, and analyze variances through natural language",
    "description": """
        LLM Tool MIS Builder - AI-Powered Financial Reporting for Odoo

        Provides 44 purpose-built tools for managing and analyzing MIS Builder
        reports through AI assistants and MCP servers. Full lifecycle coverage
        from template creation to variance analysis.

        Report Templates (6 tools):
        • List, get, create, update, delete, and duplicate report templates

        KPI Management (6 tools):
        • List, get, create, update, delete, and reorder KPIs
        • Supports MIS Builder accounting expressions (bale[], balp[], etc.)

        Custom Queries (4 tools):
        • List, create, update, and delete custom data queries

        Report Instances (6 tools):
        • List, get, create, update, delete, and duplicate instances
        • Multi-company support with configurable templates

        Periods & Columns (6 tools):
        • List, create, update, and delete period columns
        • Add comparison columns between periods
        • Add sum columns combining multiple periods

        Execution & Analysis (8 tools):
        • Compute reports and get full KPI results
        • Quick preview with ad-hoc date range
        • Drill down into specific cells for underlying records
        • Export to structured JSON format
        • Compare periods (YoY, MoM, QoQ)
        • KPI trend analysis over time
        • Account-level breakdown for any KPI
        • Variance analysis between two periods

        Annotations (4 tools):
        • List, get, set, and delete cell annotations

        Styles (4 tools):
        • List, create, update, and delete report styles

        All tools use MCP destructive/read-only hint conventions and respect
        Odoo's access control rules.
    """,
    "author": "Apexive Solutions LLC",
    "website": "https://github.com/apexive/odoo-llm",
    "license": "AGPL-3",
    "depends": [
        "llm_tool",
        "mis_builder",
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
