{
    "name": "LLM Tool Account",
    "version": "19.0.1.0.0",
    "category": "Productivity/LLM",
    "summary": "18 AI-powered accounting tools for CPAs: trial balance, tax reports, "
    "journal entries, reconciliation, payments, and period close",
    "description": """
        LLM Tool Account - AI-Powered Accounting for Odoo

        Provides 18 purpose-built accounting tools for AI assistants and MCP
        servers. Designed for CPAs, bookkeepers, and finance teams who use AI
        daily.

        Data Entry (5 tools):
        • Create journal entries, invoices, bills, credit notes, and refunds
        • Post and unpost moves with lock date enforcement
        • Reverse entries with reason tracking
        • Register payments against invoices or as direct payments

        Lookups (3 tools):
        • Find moves by reference, partner, type, date, amount, payment state
        • Search chart of accounts by code pattern, name, or type shortcut
        • Look up journals by code, name, or type

        Reports & Balances (5 tools):
        • Trial balance with flexible grouping and proper BS/P&L initial balance
        • Tax balance summary grouped by tax, partner, or journal
        • General ledger with running balance and pagination
        • Profit & Loss with comparison period and variance analysis
        • Cash position snapshot with projected cash

        Reconciliation (3 tools):
        • List unreconciled items filtered by type (bank, invoices, bills)
        • Reconcile journal items with optional write-off
        • Suggest matching debit/credit pairs

        Period Close (2 tools):
        • Pre-close checklist (draft moves, unreconciled items, lock dates)
        • Set fiscal year, tax, or period lock dates

        All tools use Odoo's native methods, respect access controls and lock
        dates, and follow MCP destructive/read-only hint conventions.
    """,
    "author": "Apexive Solutions LLC",
    "website": "https://github.com/apexive/odoo-llm",
    "license": "LGPL-3",
    "depends": [
        "llm_tool",
        "account",
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
