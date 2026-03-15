"""Tests for journal entry data entry tools"""

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestEntryTools(TransactionCase):
    """Test create, post, unpost, and reverse move tools"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.entry_tools = cls.env["account.tool.entry"]

        # Test partner
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Entry Test Partner",
                "ref": "ENTRYTEST01",
            }
        )

        # Find accounts for journal entries
        cls.receivable = cls.env["account.account"].search(
            [("account_type", "=", "asset_receivable")], limit=1
        )
        cls.income = cls.env["account.account"].search(
            [("account_type", "=", "income")], limit=1
        )
        cls.expense = cls.env["account.account"].search(
            [("account_type", "in", ("expense", "expense_direct_cost"))], limit=1
        )
        cls.payable = cls.env["account.account"].search(
            [("account_type", "=", "liability_payable")], limit=1
        )

        # Find journals
        cls.sale_journal = cls.env["account.journal"].search(
            [("type", "=", "sale")], limit=1
        )
        cls.misc_journal = cls.env["account.journal"].search(
            [("type", "=", "general")], limit=1
        )

    def test_create_entry(self):
        """Test creating a manual journal entry"""
        if not (self.receivable and self.income and self.misc_journal):
            self.skipTest("Required accounts or journal not found")

        result = self.entry_tools.account_create_move(
            move_type="entry",
            journal=self.misc_journal.code,
            date="2025-01-15",
            ref="Test entry",
            lines=[
                {
                    "account": self.receivable.code,
                    "description": "Debit line",
                    "debit": 1000.0,
                    "credit": 0.0,
                },
                {
                    "account": self.income.code,
                    "description": "Credit line",
                    "debit": 0.0,
                    "credit": 1000.0,
                },
            ],
        )

        self.assertIn("id", result)
        self.assertEqual(result["state"], "draft")
        self.assertEqual(result["move_type"], "entry")

    def test_create_invoice(self):
        """Test creating a customer invoice"""
        if not (self.income and self.sale_journal):
            self.skipTest("Required accounts or journal not found")

        result = self.entry_tools.account_create_move(
            move_type="invoice",
            partner="Entry Test Partner",
            journal=self.sale_journal.code,
            date="2025-01-15",
            lines=[
                {
                    "account": self.income.code,
                    "description": "Service revenue",
                    "quantity": 2,
                    "price": 500.0,
                },
            ],
        )

        self.assertIn("id", result)
        self.assertEqual(result["state"], "draft")
        self.assertEqual(result["partner"], "Entry Test Partner")

    def test_create_invoice_without_partner(self):
        """Test that creating an invoice without partner raises error"""
        if not self.income:
            self.skipTest("Income account not found")

        with self.assertRaises(UserError):
            self.entry_tools.account_create_move(
                move_type="invoice",
                lines=[
                    {
                        "account": self.income.code,
                        "description": "Test",
                        "quantity": 1,
                        "price": 100.0,
                    },
                ],
            )

    def test_create_move_invalid_type(self):
        """Test that invalid move_type raises error"""
        with self.assertRaises(UserError):
            self.entry_tools.account_create_move(
                move_type="invalid_type",
                lines=[],
            )

    def test_post_and_unpost(self):
        """Test posting and unposting a move"""
        if not (self.receivable and self.income and self.misc_journal):
            self.skipTest("Required accounts or journal not found")

        # Create entry
        result = self.entry_tools.account_create_move(
            move_type="entry",
            journal=self.misc_journal.code,
            date="2025-01-15",
            lines=[
                {
                    "account": self.receivable.code,
                    "description": "Debit",
                    "debit": 500.0,
                    "credit": 0.0,
                },
                {
                    "account": self.income.code,
                    "description": "Credit",
                    "debit": 0.0,
                    "credit": 500.0,
                },
            ],
        )

        move = self.env["account.move"].browse(result["id"])

        # Post
        post_result = self.entry_tools.account_post_moves(references=[move.name])
        self.assertEqual(post_result["posted_count"], 1)
        self.assertEqual(move.state, "posted")

        # Unpost
        unpost_result = self.entry_tools.account_unpost_moves(references=[move.name])
        self.assertEqual(unpost_result["unposted_count"], 1)
        self.assertEqual(move.state, "draft")

    def test_reverse_move(self):
        """Test reversing a posted move"""
        if not (self.receivable and self.income and self.misc_journal):
            self.skipTest("Required accounts or journal not found")

        # Create and post entry
        result = self.entry_tools.account_create_move(
            move_type="entry",
            journal=self.misc_journal.code,
            date="2025-01-15",
            lines=[
                {
                    "account": self.receivable.code,
                    "description": "Debit",
                    "debit": 300.0,
                    "credit": 0.0,
                },
                {
                    "account": self.income.code,
                    "description": "Credit",
                    "debit": 0.0,
                    "credit": 300.0,
                },
            ],
        )
        move = self.env["account.move"].browse(result["id"])
        move.action_post()

        # Reverse
        rev_result = self.entry_tools.account_reverse_move(
            reference=move.name,
            date="2025-01-31",
            reason="Correction",
        )

        self.assertIn("reversal_move", rev_result)
        self.assertTrue(rev_result["reversal_move"])
        self.assertEqual(rev_result["state"], "posted")

    def test_reverse_draft_move_raises(self):
        """Test that reversing a draft move raises error"""
        if not (self.receivable and self.income and self.misc_journal):
            self.skipTest("Required accounts or journal not found")

        result = self.entry_tools.account_create_move(
            move_type="entry",
            journal=self.misc_journal.code,
            date="2025-01-15",
            lines=[
                {
                    "account": self.receivable.code,
                    "description": "Debit",
                    "debit": 100.0,
                    "credit": 0.0,
                },
                {
                    "account": self.income.code,
                    "description": "Credit",
                    "debit": 0.0,
                    "credit": 100.0,
                },
            ],
        )
        move = self.env["account.move"].browse(result["id"])

        with self.assertRaises(UserError):
            self.entry_tools.account_reverse_move(reference=move.name)
