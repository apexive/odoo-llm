"""Report tools: profit & loss and cash position"""

import logging
from typing import Optional

from odoo import models

from odoo.addons.llm_tool.decorators import llm_tool

_logger = logging.getLogger(__name__)

INCOME_TYPES = ("income", "income_other")
EXPENSE_TYPES = ("expense", "expense_depreciation", "expense_direct_cost")


class AccountReport(models.Model):
    _name = "account.tool.report"
    _inherit = "account.tool.mixin"
    _description = "LLM tools for financial reports"

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def account_get_profit_and_loss(
        self,
        date_from: str,
        date_to: str,
        compare_date_from: Optional[str] = None,
        compare_date_to: Optional[str] = None,
        target_move: str = "posted",
        group_by: str = "account",
    ) -> dict:
        """Get Profit & Loss (Income Statement) report

        Returns revenue, expenses, and net income for the period. Optionally
        includes a comparison period with variance analysis.

        Args:
            date_from: Period start date (YYYY-MM-DD)
            date_to: Period end date (YYYY-MM-DD)
            compare_date_from: Comparison period start (optional, YYYY-MM-DD)
            compare_date_to: Comparison period end (optional, YYYY-MM-DD)
            target_move: "posted" (default) or "all" entries
            group_by: "account" (default) or "account_type"

        Returns:
            Dictionary with income, expense, and net income breakdown
        """
        MoveLine = self.env["account.move.line"]

        # Get P&L accounts
        income_accounts = self.env["account.account"].search(
            [("account_type", "in", INCOME_TYPES)]
        )
        expense_accounts = self.env["account.account"].search(
            [("account_type", "in", EXPENSE_TYPES)]
        )

        base_domain = []
        if target_move == "posted":
            base_domain.append(("parent_state", "=", "posted"))

        # Current period
        income_rows = self._aggregate_pl(
            MoveLine, income_accounts, date_from, date_to, base_domain, group_by
        )
        expense_rows = self._aggregate_pl(
            MoveLine, expense_accounts, date_from, date_to, base_domain, group_by
        )

        revenue_total = sum(r["amount"] for r in income_rows)
        expense_total = sum(r["amount"] for r in expense_rows)
        net_income = revenue_total + expense_total  # expenses are negative

        result = {
            "date_from": date_from,
            "date_to": date_to,
            "target_move": target_move,
            "income": income_rows,
            "revenue_total": revenue_total,
            "expenses": expense_rows,
            "expense_total": expense_total,
            "net_income": net_income,
        }

        # Comparison period
        if compare_date_from and compare_date_to:
            cmp_income = self._aggregate_pl(
                MoveLine,
                income_accounts,
                compare_date_from,
                compare_date_to,
                base_domain,
                group_by,
            )
            cmp_expense = self._aggregate_pl(
                MoveLine,
                expense_accounts,
                compare_date_from,
                compare_date_to,
                base_domain,
                group_by,
            )

            cmp_revenue = sum(r["amount"] for r in cmp_income)
            cmp_expense_total = sum(r["amount"] for r in cmp_expense)
            cmp_net = cmp_revenue + cmp_expense_total

            result["comparison"] = {
                "date_from": compare_date_from,
                "date_to": compare_date_to,
                "income": cmp_income,
                "revenue_total": cmp_revenue,
                "expenses": cmp_expense,
                "expense_total": cmp_expense_total,
                "net_income": cmp_net,
            }
            result["variance"] = {
                "revenue": revenue_total - cmp_revenue,
                "revenue_pct": (
                    round((revenue_total - cmp_revenue) / abs(cmp_revenue) * 100, 1)
                    if cmp_revenue
                    else None
                ),
                "expense": expense_total - cmp_expense_total,
                "expense_pct": (
                    round(
                        (expense_total - cmp_expense_total)
                        / abs(cmp_expense_total)
                        * 100,
                        1,
                    )
                    if cmp_expense_total
                    else None
                ),
                "net_income": net_income - cmp_net,
                "net_income_pct": (
                    round((net_income - cmp_net) / abs(cmp_net) * 100, 1)
                    if cmp_net
                    else None
                ),
            }

        return result

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def account_get_cash_position(self) -> dict:
        """Get current cash position snapshot

        Returns current balances of all bank and cash accounts, plus
        outstanding incoming and outgoing payments for a projected
        cash position.

        Returns:
            Dictionary with bank/cash balances and projected position
        """
        MoveLine = self.env["account.move.line"]

        # Bank/cash account balances (posted, all time)
        bank_accounts = self.env["account.account"].search(
            [("account_type", "=", "asset_cash")]
        )

        bank_balances = []
        total_cash = 0.0

        if bank_accounts:
            groups = MoveLine._read_group(
                domain=[
                    ("account_id", "in", bank_accounts.ids),
                    ("parent_state", "=", "posted"),
                ],
                groupby=["account_id"],
                aggregates=["balance:sum"],
            )
            for account, balance_sum in groups:
                bal = balance_sum or 0.0
                bank_balances.append(
                    {
                        "account_code": account.code,
                        "account_name": account.name,
                        "balance": bal,
                    }
                )
                total_cash += bal

        # Outstanding incoming payments (unreconciled debit on receivable from payments)
        outstanding_in = 0.0
        receivable_accounts = self.env["account.account"].search(
            [("account_type", "=", "asset_receivable")]
        )
        if receivable_accounts:
            groups = MoveLine._read_group(
                domain=[
                    ("account_id", "in", receivable_accounts.ids),
                    ("parent_state", "=", "posted"),
                    ("reconciled", "=", False),
                    ("amount_residual", ">", 0),
                ],
                groupby=[],
                aggregates=["amount_residual:sum"],
            )
            if groups:
                outstanding_in = groups[0][0] or 0.0

        # Outstanding outgoing payments (unreconciled credit on payable from payments)
        outstanding_out = 0.0
        payable_accounts = self.env["account.account"].search(
            [("account_type", "=", "liability_payable")]
        )
        if payable_accounts:
            groups = MoveLine._read_group(
                domain=[
                    ("account_id", "in", payable_accounts.ids),
                    ("parent_state", "=", "posted"),
                    ("reconciled", "=", False),
                    ("amount_residual", "<", 0),
                ],
                groupby=[],
                aggregates=["amount_residual:sum"],
            )
            if groups:
                outstanding_out = abs(groups[0][0] or 0.0)

        projected = total_cash + outstanding_in - outstanding_out

        return {
            "bank_accounts": bank_balances,
            "total_cash": total_cash,
            "outstanding_incoming": outstanding_in,
            "outstanding_outgoing": outstanding_out,
            "projected_cash": projected,
        }

    def _aggregate_pl(
        self, MoveLine, accounts, date_from, date_to, base_domain, group_by
    ):
        """Aggregate P&L lines by account or account_type."""
        domain = [
            ("account_id", "in", accounts.ids),
            ("date", ">=", date_from),
            ("date", "<=", date_to),
        ] + base_domain

        if group_by == "account_type":
            # Group by account, then aggregate by type
            groups = MoveLine._read_group(
                domain=domain,
                groupby=["account_id"],
                aggregates=["balance:sum"],
            )
            type_totals = {}
            for account, balance_sum in groups:
                atype = account.account_type
                if atype not in type_totals:
                    type_totals[atype] = 0.0
                type_totals[atype] += balance_sum or 0.0

            return [
                {"account_type": atype, "amount": amt}
                for atype, amt in sorted(type_totals.items())
            ]
        else:
            groups = MoveLine._read_group(
                domain=domain,
                groupby=["account_id"],
                aggregates=["balance:sum"],
            )
            return [
                {
                    "account_code": account.code,
                    "account_name": account.name,
                    "amount": balance_sum or 0.0,
                }
                for account, balance_sum in groups
            ]
