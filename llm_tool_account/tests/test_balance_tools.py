"""Tests for balance and report tools"""

from odoo.tests.common import TransactionCase


class TestBalanceTools(TransactionCase):
    """Test trial balance and financial report tools"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.balance_tools = cls.env["account.tool.balance"]
        cls.report_tools = cls.env["account.tool.report"]
        cls.tax_tools = cls.env["account.tool.tax.balance"]

        # Create test data: a posted journal entry
        cls.receivable = cls.env["account.account"].search(
            [("account_type", "=", "asset_receivable")], limit=1
        )
        cls.income = cls.env["account.account"].search(
            [("account_type", "=", "income")], limit=1
        )
        cls.misc_journal = cls.env["account.journal"].search(
            [("type", "=", "general")], limit=1
        )

        if cls.receivable and cls.income and cls.misc_journal:
            move = cls.env["account.move"].create(
                {
                    "move_type": "entry",
                    "journal_id": cls.misc_journal.id,
                    "date": "2025-06-15",
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "account_id": cls.receivable.id,
                                "name": "Test debit",
                                "debit": 1000.0,
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
                                "credit": 1000.0,
                            },
                        ),
                    ],
                }
            )
            move.action_post()
            cls.test_move = move

    def test_get_balances_all(self):
        """Test trial balance for all accounts"""
        result = self.balance_tools.account_get_balances(
            date_from="2025-01-01",
            date_to="2025-12-31",
        )
        self.assertIn("rows", result)
        self.assertIn("totals", result)
        self.assertIn("row_count", result)

    def test_get_balances_by_account_type(self):
        """Test trial balance filtered by account type"""
        result = self.balance_tools.account_get_balances(
            date_from="2025-01-01",
            date_to="2025-12-31",
            accounts="receivable",
        )
        self.assertIn("rows", result)
        for row in result["rows"]:
            if "account_code" in row:
                account = self.env["account.account"].search(
                    [("code", "=", row["account_code"])], limit=1
                )
                self.assertEqual(account.account_type, "asset_receivable")

    def test_get_balances_group_by_partner(self):
        """Test trial balance grouped by partner"""
        result = self.balance_tools.account_get_balances(
            date_from="2025-01-01",
            date_to="2025-12-31",
            accounts="receivable",
            group_by=["partner"],
        )
        self.assertIn("rows", result)
        self.assertEqual(result["group_by"], ["partner"])

    def test_get_balances_hide_zero(self):
        """Test that zero balance rows are hidden by default"""
        result = self.balance_tools.account_get_balances(
            date_from="2025-01-01",
            date_to="2025-12-31",
            hide_zero=True,
        )
        for row in result["rows"]:
            has_values = (
                row["initial_balance"]
                or row["debit"]
                or row["credit"]
                or row["ending_balance"]
            )
            self.assertTrue(has_values)

    def test_get_profit_and_loss(self):
        """Test P&L report"""
        result = self.report_tools.account_get_profit_and_loss(
            date_from="2025-01-01",
            date_to="2025-12-31",
        )
        self.assertIn("income", result)
        self.assertIn("expenses", result)
        self.assertIn("net_income", result)
        self.assertIn("revenue_total", result)
        self.assertIn("expense_total", result)

    def test_get_profit_and_loss_with_comparison(self):
        """Test P&L with comparison period"""
        result = self.report_tools.account_get_profit_and_loss(
            date_from="2025-01-01",
            date_to="2025-12-31",
            compare_date_from="2024-01-01",
            compare_date_to="2024-12-31",
        )
        self.assertIn("comparison", result)
        self.assertIn("variance", result)

    def test_get_cash_position(self):
        """Test cash position snapshot"""
        result = self.report_tools.account_get_cash_position()
        self.assertIn("bank_accounts", result)
        self.assertIn("total_cash", result)
        self.assertIn("outstanding_incoming", result)
        self.assertIn("outstanding_outgoing", result)
        self.assertIn("projected_cash", result)

    def test_get_tax_balances(self):
        """Test tax balance summary"""
        result = self.tax_tools.account_get_tax_balances(
            date_from="2025-01-01",
            date_to="2025-12-31",
        )
        self.assertIn("rows", result)
        self.assertIn("totals", result)
        self.assertIn("row_count", result)
