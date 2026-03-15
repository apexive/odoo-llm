"""Tests for payment registration tools"""

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestPaymentTools(TransactionCase):
    """Test payment registration tools"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.payment_tools = cls.env["account.tool.payment"]

        # Test partner
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Payment Test Partner",
            }
        )

        # Find required accounts and journals
        cls.receivable = cls.env["account.account"].search(
            [("account_type", "=", "asset_receivable")], limit=1
        )
        cls.income = cls.env["account.account"].search(
            [("account_type", "=", "income")], limit=1
        )
        cls.sale_journal = cls.env["account.journal"].search(
            [("type", "=", "sale")], limit=1
        )
        cls.bank_journal = cls.env["account.journal"].search(
            [("type", "=", "bank")], limit=1
        )

    def _create_posted_invoice(self, amount=1000.0):
        """Helper to create a posted customer invoice"""
        if not (self.receivable and self.income and self.sale_journal):
            self.skipTest("Required accounts or journal not found")

        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "journal_id": self.sale_journal.id,
                "date": "2025-06-15",
                "invoice_date": "2025-06-15",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": self.income.id,
                            "name": "Test service",
                            "quantity": 1,
                            "price_unit": amount,
                        },
                    ),
                ],
            }
        )
        move.action_post()
        return move

    def test_register_payment_for_invoice(self):
        """Test paying a single invoice"""
        if not self.bank_journal:
            self.skipTest("Bank journal not found")

        invoice = self._create_posted_invoice()

        result = self.payment_tools.account_register_payment(
            move_references=[invoice.name],
            journal=self.bank_journal.code,
            date="2025-06-20",
        )

        self.assertIn("message", result)
        # Verify invoice is paid
        invoice.invalidate_recordset()
        self.assertIn(invoice.payment_state, ("paid", "in_payment"))

    def test_register_direct_payment(self):
        """Test creating a direct payment without invoice"""
        if not self.bank_journal:
            self.skipTest("Bank journal not found")

        result = self.payment_tools.account_register_payment(
            partner="Payment Test Partner",
            amount=500.0,
            journal=self.bank_journal.code,
            date="2025-06-20",
            memo="Advance payment",
        )

        self.assertIn("payment_id", result)
        self.assertEqual(result["amount"], 500.0)
        self.assertEqual(result["state"], "posted")

    def test_register_payment_missing_params(self):
        """Test that missing required params raises error"""
        with self.assertRaises(UserError):
            self.payment_tools.account_register_payment()

    def test_register_payment_nonexistent_invoice(self):
        """Test paying a non-existent invoice"""
        with self.assertRaises(UserError):
            self.payment_tools.account_register_payment(
                move_references=["NONEXISTENT/2025/9999"],
            )
