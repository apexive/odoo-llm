"""Shared helpers for accounting LLM tools"""

import logging
from datetime import date

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

ACCOUNT_TYPE_SHORTCUTS = {
    "receivable": [("account_type", "=", "asset_receivable")],
    "payable": [("account_type", "=", "liability_payable")],
    "bank": [("account_type", "=", "asset_cash")],
    "cash": [("account_type", "=", "asset_cash")],
    "equity": [("account_type", "in", ("equity", "equity_unaffected"))],
    "income": [("account_type", "in", ("income", "income_other"))],
    "expense": [
        (
            "account_type",
            "in",
            ("expense", "expense_depreciation", "expense_direct_cost"),
        )
    ],
    "asset": [
        (
            "account_type",
            "in",
            (
                "asset_receivable",
                "asset_cash",
                "asset_current",
                "asset_non_current",
                "asset_prepayments",
                "asset_fixed",
            ),
        )
    ],
    "liability": [
        (
            "account_type",
            "in",
            (
                "liability_payable",
                "liability_credit_card",
                "liability_current",
                "liability_non_current",
            ),
        )
    ],
}

# Account types that carry initial balance from all time (balance sheet)
BS_ACCOUNT_TYPES = {
    "asset_receivable",
    "asset_cash",
    "asset_current",
    "asset_non_current",
    "asset_prepayments",
    "asset_fixed",
    "liability_payable",
    "liability_credit_card",
    "liability_current",
    "liability_non_current",
    "equity",
    "equity_unaffected",
    "off_balance",
}


class AccountToolMixin(models.AbstractModel):
    _name = "account.tool.mixin"
    _description = "Shared helpers for accounting LLM tools"

    def _resolve_accounts(self, identifier):
        """Resolve accounts by code pattern, name, or type shortcut.

        Args:
            identifier: Account code (exact or LIKE pattern with %),
                        type shortcut (receivable, payable, bank, etc.),
                        or "all" for all accounts.

        Returns:
            account.account recordset
        """
        Account = self.env["account.account"]

        if not identifier or identifier == "all":
            return Account.search([])

        # Check type shortcuts first
        shortcut = identifier.lower()
        if shortcut in ACCOUNT_TYPE_SHORTCUTS:
            return Account.search(ACCOUNT_TYPE_SHORTCUTS[shortcut])

        # Code pattern (exact or LIKE)
        if "%" in identifier:
            accounts = Account.search([("code", "=like", identifier)])
        else:
            accounts = Account.search([("code", "=", identifier)])

        if not accounts:
            # Try name search as fallback
            accounts = Account.search([("name", "ilike", identifier)])

        if not accounts:
            raise UserError(_("No accounts found matching '%s'") % identifier)
        return accounts

    def _resolve_partner(self, identifier):
        """Resolve a partner by name, ref, or VAT number.

        Args:
            identifier: Partner name (ilike), ref (exact), or VAT (exact).

        Returns:
            res.partner record (single)
        """
        Partner = self.env["res.partner"]

        partner = Partner.search([("name", "ilike", identifier)], limit=1)
        if not partner:
            partner = Partner.search([("ref", "=", identifier)], limit=1)
        if not partner:
            partner = Partner.search([("vat", "=", identifier)], limit=1)
        if not partner:
            raise UserError(_("Partner '%s' not found") % identifier)
        return partner

    def _resolve_journal(self, identifier):
        """Resolve a journal by code, name, or type.

        Args:
            identifier: Journal code (exact, case-insensitive),
                        name (ilike), or type (sale/purchase/cash/bank/general).

        Returns:
            account.journal record (single)
        """
        Journal = self.env["account.journal"]

        # Try code first (case-insensitive)
        journal = Journal.search([("code", "=ilike", identifier)], limit=1)
        if not journal:
            journal = Journal.search([("name", "ilike", identifier)], limit=1)
        if not journal:
            valid_types = ("sale", "purchase", "cash", "bank", "general")
            if identifier.lower() in valid_types:
                journal = Journal.search([("type", "=", identifier.lower())], limit=1)
        if not journal:
            raise UserError(_("Journal '%s' not found") % identifier)
        return journal

    def _resolve_tax(self, identifier):
        """Resolve a tax by name.

        Args:
            identifier: Tax name (ilike search).

        Returns:
            account.tax record (single)
        """
        tax = self.env["account.tax"].search([("name", "ilike", identifier)], limit=1)
        if not tax:
            raise UserError(_("Tax '%s' not found") % identifier)
        return tax

    def _resolve_move(self, reference):
        """Resolve an account move by its name/reference.

        Args:
            reference: Move name (exact match, e.g. 'INV/2025/0001').

        Returns:
            account.move record (single)
        """
        move = self.env["account.move"].search([("name", "=", reference)], limit=1)
        if not move:
            raise UserError(_("Move '%s' not found") % reference)
        return move

    def _get_posted_domain(self, date_from=None, date_to=None, target_move="posted"):
        """Build base domain for journal item queries.

        Args:
            date_from: Start date (inclusive).
            date_to: End date (inclusive).
            target_move: "posted" for posted entries only, "all" for all.

        Returns:
            list of domain tuples
        """
        domain = []
        if target_move == "posted":
            domain.append(("parent_state", "=", "posted"))
        elif target_move == "all":
            domain.append(("parent_state", "!=", "cancel"))
        if date_from:
            domain.append(("date", ">=", date_from))
        if date_to:
            domain.append(("date", "<=", date_to))
        return domain

    def _get_fy_start_date(self, for_date, company=None):
        """Get the fiscal year start date for a given date.

        Args:
            for_date: The date to find the fiscal year for.
            company: Company record (defaults to current company).

        Returns:
            date: Fiscal year start date.
        """
        if company is None:
            company = self.env.company
        if isinstance(for_date, str):
            for_date = date.fromisoformat(for_date)
        fy_dates = company.compute_fiscalyear_dates(for_date)
        return fy_dates["date_from"]

    def _is_bs_account(self, account):
        """Check if an account is a balance sheet account (carries initial balance)."""
        return account.account_type in BS_ACCOUNT_TYPES
