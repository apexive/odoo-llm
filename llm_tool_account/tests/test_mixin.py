"""Tests for account tool mixin resolver methods"""

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestAccountToolMixin(TransactionCase):
    """Test shared resolver methods in AccountToolMixin"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mixin = cls.env["account.tool.mixin"]

        # Find existing accounts for testing
        cls.receivable_account = cls.env["account.account"].search(
            [("account_type", "=", "asset_receivable")], limit=1
        )
        cls.bank_account = cls.env["account.account"].search(
            [("account_type", "=", "asset_cash")], limit=1
        )
        cls.expense_account = cls.env["account.account"].search(
            [
                (
                    "account_type",
                    "in",
                    ("expense", "expense_depreciation", "expense_direct_cost"),
                )
            ],
            limit=1,
        )

        # Test partner
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test LLM Partner",
                "ref": "LLMTEST01",
            }
        )

        # Find existing journals
        cls.bank_journal = cls.env["account.journal"].search(
            [("type", "=", "bank")], limit=1
        )
        cls.sale_journal = cls.env["account.journal"].search(
            [("type", "=", "sale")], limit=1
        )

    def test_resolve_accounts_by_type_shortcut(self):
        """Test resolving accounts by type shortcut"""
        accounts = self.mixin._resolve_accounts("receivable")
        self.assertTrue(accounts)
        for acc in accounts:
            self.assertEqual(acc.account_type, "asset_receivable")

    def test_resolve_accounts_by_code(self):
        """Test resolving accounts by exact code"""
        if self.receivable_account:
            accounts = self.mixin._resolve_accounts(self.receivable_account.code)
            self.assertEqual(len(accounts), 1)
            self.assertEqual(accounts.id, self.receivable_account.id)

    def test_resolve_accounts_by_pattern(self):
        """Test resolving accounts by code pattern"""
        if self.receivable_account:
            prefix = self.receivable_account.code[:1]
            accounts = self.mixin._resolve_accounts(f"{prefix}%")
            self.assertTrue(accounts)
            for acc in accounts:
                self.assertTrue(acc.code.startswith(prefix))

    def test_resolve_accounts_all(self):
        """Test resolving all accounts"""
        accounts = self.mixin._resolve_accounts("all")
        self.assertTrue(accounts)

    def test_resolve_accounts_not_found(self):
        """Test resolving non-existent account"""
        with self.assertRaises(UserError):
            self.mixin._resolve_accounts("ZZZNOTEXIST999")

    def test_resolve_partner_by_name(self):
        """Test resolving partner by name"""
        partner = self.mixin._resolve_partner("Test LLM Partner")
        self.assertEqual(partner.id, self.partner.id)

    def test_resolve_partner_by_ref(self):
        """Test resolving partner by ref"""
        partner = self.mixin._resolve_partner("LLMTEST01")
        self.assertEqual(partner.id, self.partner.id)

    def test_resolve_partner_not_found(self):
        """Test resolving non-existent partner"""
        with self.assertRaises(UserError):
            self.mixin._resolve_partner("NonExistentPartner999")

    def test_resolve_journal_by_type(self):
        """Test resolving journal by type"""
        if self.bank_journal:
            journal = self.mixin._resolve_journal("bank")
            self.assertEqual(journal.type, "bank")

    def test_resolve_journal_by_code(self):
        """Test resolving journal by code"""
        if self.bank_journal:
            journal = self.mixin._resolve_journal(self.bank_journal.code)
            self.assertEqual(journal.id, self.bank_journal.id)

    def test_resolve_journal_not_found(self):
        """Test resolving non-existent journal"""
        with self.assertRaises(UserError):
            self.mixin._resolve_journal("ZZZNOTEXIST")

    def test_get_posted_domain(self):
        """Test building posted domain"""
        domain = self.mixin._get_posted_domain(
            date_from="2025-01-01",
            date_to="2025-12-31",
            target_move="posted",
        )
        self.assertIn(("parent_state", "=", "posted"), domain)
        self.assertIn(("date", ">=", "2025-01-01"), domain)
        self.assertIn(("date", "<=", "2025-12-31"), domain)

    def test_get_posted_domain_all(self):
        """Test building domain with all moves"""
        domain = self.mixin._get_posted_domain(target_move="all")
        self.assertIn(("parent_state", "!=", "cancel"), domain)

    def test_get_fy_start_date(self):
        """Test fiscal year start date"""
        from datetime import date

        fy_start = self.mixin._get_fy_start_date("2025-06-15")
        self.assertIsInstance(fy_start, date)
        # FY start should be on or before the given date
        self.assertLessEqual(fy_start, date(2025, 6, 15))

    def test_is_bs_account(self):
        """Test balance sheet account detection"""
        if self.receivable_account:
            self.assertTrue(self.mixin._is_bs_account(self.receivable_account))
        if self.expense_account:
            self.assertFalse(self.mixin._is_bs_account(self.expense_account))
