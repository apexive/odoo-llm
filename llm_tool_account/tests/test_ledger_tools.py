"""Tests for ledger and reconciliation tools"""

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestLedgerTools(TransactionCase):
    """Test ledger, lookup, reconciliation, and period tools"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ledger_tools = cls.env["account.tool.ledger"]
        cls.lookup_tools = cls.env["account.tool.lookup"]
        cls.reconcile_tools = cls.env["account.tool.reconcile"]
        cls.period_tools = cls.env["account.tool.period"]

        # Find accounts and journals
        cls.receivable = cls.env["account.account"].search(
            [("account_type", "=", "asset_receivable")], limit=1
        )
        cls.income = cls.env["account.account"].search(
            [("account_type", "=", "income")], limit=1
        )
        cls.misc_journal = cls.env["account.journal"].search(
            [("type", "=", "general")], limit=1
        )

        # Create a posted test move
        if cls.receivable and cls.income and cls.misc_journal:
            move = cls.env["account.move"].create(
                {
                    "move_type": "entry",
                    "journal_id": cls.misc_journal.id,
                    "date": "2025-06-15",
                    "ref": "Ledger test entry",
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "account_id": cls.receivable.id,
                                "name": "Test debit",
                                "debit": 750.0,
                                "credit": 0.0,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "account_id": cls.income.id,
                                "name": "Test credit",
                                "debit": 0.0,
                                "credit": 750.0,
                            },
                        ),
                    ],
                }
            )
            move.action_post()
            cls.test_move = move

    # -- Ledger tests --

    def test_get_ledger(self):
        """Test basic general ledger"""
        if not self.receivable:
            self.skipTest("Receivable account not found")

        result = self.ledger_tools.account_get_ledger(
            accounts=self.receivable.code,
            date_from="2025-01-01",
            date_to="2025-12-31",
        )
        self.assertIn("items", result)
        self.assertIn("initial_balance", result)
        self.assertIn("accounts", result)

    def test_get_ledger_pagination(self):
        """Test ledger with limit and offset"""
        if not self.receivable:
            self.skipTest("Receivable account not found")

        result = self.ledger_tools.account_get_ledger(
            accounts=self.receivable.code,
            date_from="2025-01-01",
            date_to="2025-12-31",
            limit=5,
            offset=0,
        )
        self.assertIn("has_more", result)
        self.assertIn("total_count", result)

    def test_get_ledger_not_found(self):
        """Test ledger with non-existent account"""
        with self.assertRaises(UserError):
            self.ledger_tools.account_get_ledger(
                accounts="ZZZNOTEXIST999",
                date_from="2025-01-01",
                date_to="2025-12-31",
            )

    # -- Lookup tests --

    def test_find_moves(self):
        """Test finding moves"""
        result = self.lookup_tools.account_find_moves(
            state="posted",
            date_from="2025-01-01",
            date_to="2025-12-31",
            limit=10,
        )
        self.assertIn("moves", result)
        self.assertIn("count", result)

    def test_find_accounts(self):
        """Test finding accounts"""
        result = self.lookup_tools.account_find_accounts(
            account_type="receivable",
        )
        self.assertIn("accounts", result)
        self.assertTrue(result["count"] > 0)

    def test_find_accounts_with_balance(self):
        """Test finding accounts with balance"""
        result = self.lookup_tools.account_find_accounts(
            account_type="receivable",
            include_balance=True,
        )
        self.assertIn("accounts", result)
        if result["accounts"]:
            self.assertIn("balance", result["accounts"][0])

    def test_find_journals(self):
        """Test finding journals"""
        result = self.lookup_tools.account_find_journals(
            journal_type="bank",
        )
        self.assertIn("journals", result)
        for j in result["journals"]:
            self.assertEqual(j["type"], "bank")

    # -- Reconciliation tests --

    def test_get_unreconciled(self):
        """Test listing unreconciled items"""
        result = self.reconcile_tools.account_get_unreconciled(type="all")
        self.assertIn("items", result)
        self.assertIn("count", result)

    def test_get_unreconciled_by_type(self):
        """Test listing unreconciled bank items"""
        result = self.reconcile_tools.account_get_unreconciled(type="bank")
        self.assertIn("items", result)

    def test_suggest_matches(self):
        """Test suggesting matches"""
        if not self.receivable:
            self.skipTest("Receivable account not found")

        result = self.reconcile_tools.account_suggest_matches(
            account=self.receivable.code,
        )
        self.assertIn("suggestions", result)
        self.assertIn("account_code", result)

    def test_reconcile_too_few_lines(self):
        """Test that reconciling with <2 lines raises error"""
        with self.assertRaises(UserError):
            self.reconcile_tools.account_reconcile(line_ids=[1])

    # -- Period close tests --

    def test_check_period(self):
        """Test period close checklist"""
        result = self.period_tools.account_check_period(
            date_from="2025-01-01",
            date_to="2025-12-31",
        )
        self.assertIn("checks", result)
        self.assertIn("lock_dates", result)
        self.assertIn("ready_to_close", result)
        self.assertEqual(len(result["checks"]), 3)
