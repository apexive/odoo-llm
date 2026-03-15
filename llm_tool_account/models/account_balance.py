"""Balance tools: trial balance with flexible grouping"""

import logging
from collections import defaultdict
from datetime import date as date_type
from typing import Optional

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.llm_tool.decorators import llm_tool

_logger = logging.getLogger(__name__)

VALID_GROUP_BY = ("account", "partner", "currency", "journal", "account_type")

GROUP_BY_FIELD_MAP = {
    "account": "account_id",
    "partner": "partner_id",
    "currency": "currency_id",
    "journal": "journal_id",
    "account_type": "account_id",  # grouped post-query
}


class AccountBalance(models.Model):
    _name = "account.tool.balance"
    _inherit = "account.tool.mixin"
    _description = "LLM tools for trial balance"

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def account_get_balances(
        self,
        date_from: str,
        date_to: str,
        accounts: str = "all",
        partner: Optional[str] = None,
        journal: Optional[str] = None,
        target_move: str = "posted",
        group_by: Optional[list] = None,
        aging: bool = False,
        hide_zero: bool = True,
    ) -> dict:
        """Get trial balance with flexible grouping

        Returns initial balance, period movement (debit/credit), and ending
        balance for each group. Supports grouping by account, partner,
        journal, currency, or account type.

        For receivable/payable accounts with aging=True, adds aging buckets
        (current, 1-30, 31-60, 61-90, 90+) based on due dates.

        Args:
            date_from: Period start date (YYYY-MM-DD)
            date_to: Period end date (YYYY-MM-DD)
            accounts: Account filter - code pattern ("6%"), type shortcut
                      ("receivable", "expense", etc.), or "all" (default)
            partner: Filter by partner name (optional)
            journal: Filter by journal code/name (optional)
            target_move: "posted" (default) or "all" entries
            group_by: Grouping fields list. Options: "account" (default),
                      "partner", "currency", "journal", "account_type"
            aging: Add aging buckets for receivable/payable (default: False)
            hide_zero: Hide rows where all amounts are zero (default: True)

        Returns:
            Dictionary with balance rows and totals
        """
        if group_by is None:
            group_by = ["account"]
        for gb in group_by:
            if gb not in VALID_GROUP_BY:
                raise UserError(
                    _("Invalid group_by '%s'. Use: %s")
                    % (gb, ", ".join(VALID_GROUP_BY))
                )

        resolved_accounts = self._resolve_accounts(accounts)
        account_ids = resolved_accounts.ids

        # Build extra domain filters
        extra_domain = []
        if partner:
            extra_domain.append(("partner_id", "=", self._resolve_partner(partner).id))
        if journal:
            extra_domain.append(("journal_id", "=", self._resolve_journal(journal).id))

        # Compute initial balances
        initial_data = self._compute_initial_balances(
            account_ids, date_from, target_move, extra_domain, group_by
        )

        # Compute period movement
        period_data = self._compute_period_balances(
            account_ids, date_from, date_to, target_move, extra_domain, group_by
        )

        # Merge initial + period
        all_keys = set(initial_data.keys()) | set(period_data.keys())
        rows = []
        totals = {
            "initial_balance": 0.0,
            "debit": 0.0,
            "credit": 0.0,
            "ending_balance": 0.0,
        }

        for key in sorted(all_keys):
            init = initial_data.get(key, {"balance": 0.0})
            period = period_data.get(key, {"debit": 0.0, "credit": 0.0, "balance": 0.0})

            initial_balance = init["balance"]
            debit = period["debit"]
            credit = period["credit"]
            ending_balance = initial_balance + period["balance"]

            if hide_zero and not (initial_balance or debit or credit or ending_balance):
                continue

            row = {
                **self._format_group_key(key, group_by),
                "initial_balance": initial_balance,
                "debit": debit,
                "credit": credit,
                "ending_balance": ending_balance,
            }
            rows.append(row)

            totals["initial_balance"] += initial_balance
            totals["debit"] += debit
            totals["credit"] += credit
            totals["ending_balance"] += ending_balance

        result = {
            "date_from": date_from,
            "date_to": date_to,
            "target_move": target_move,
            "group_by": group_by,
            "rows": rows,
            "totals": totals,
            "row_count": len(rows),
        }

        # Add aging if requested
        if aging:
            aging_data = self._compute_aging(
                account_ids, date_to, extra_domain, group_by
            )
            if aging_data:
                result["aging"] = aging_data

        return result

    def _compute_initial_balances(
        self, account_ids, date_from, target_move, extra_domain, group_by
    ):
        """Compute initial balances (before date_from).

        BS accounts: all time before date_from.
        P&L accounts: from fiscal year start to date_from.
        """
        MoveLine = self.env["account.move.line"]
        result = defaultdict(lambda: {"balance": 0.0})

        # Split accounts by BS vs P&L
        accounts = self.env["account.account"].browse(account_ids)
        bs_ids = [a.id for a in accounts if self._is_bs_account(a)]
        pl_ids = [a.id for a in accounts if not self._is_bs_account(a)]

        groupby_fields = self._get_groupby_fields(group_by)

        # BS accounts: all time < date_from
        if bs_ids:
            domain = [
                ("account_id", "in", bs_ids),
                ("date", "<", date_from),
            ] + extra_domain
            if target_move == "posted":
                domain.append(("parent_state", "=", "posted"))

            groups = MoveLine._read_group(
                domain=domain,
                groupby=groupby_fields,
                aggregates=["balance:sum"],
            )
            for *fields, balance_sum in groups:
                key = self._make_group_key(fields, groupby_fields, group_by)
                result[key]["balance"] += balance_sum or 0.0

        # P&L accounts: from FY start to date_from
        if pl_ids:
            fy_start = self._get_fy_start_date(date_from)
            domain = [
                ("account_id", "in", pl_ids),
                ("date", ">=", str(fy_start)),
                ("date", "<", date_from),
            ] + extra_domain
            if target_move == "posted":
                domain.append(("parent_state", "=", "posted"))

            groups = MoveLine._read_group(
                domain=domain,
                groupby=groupby_fields,
                aggregates=["balance:sum"],
            )
            for *fields, balance_sum in groups:
                key = self._make_group_key(fields, groupby_fields, group_by)
                result[key]["balance"] += balance_sum or 0.0

        return dict(result)

    def _compute_period_balances(
        self, account_ids, date_from, date_to, target_move, extra_domain, group_by
    ):
        """Compute period movement (debit, credit, balance)."""
        MoveLine = self.env["account.move.line"]
        groupby_fields = self._get_groupby_fields(group_by)

        domain = [
            ("account_id", "in", account_ids),
            ("date", ">=", date_from),
            ("date", "<=", date_to),
        ] + extra_domain
        if target_move == "posted":
            domain.append(("parent_state", "=", "posted"))

        groups = MoveLine._read_group(
            domain=domain,
            groupby=groupby_fields,
            aggregates=["debit:sum", "credit:sum", "balance:sum"],
        )

        result = {}
        for *fields, debit_sum, credit_sum, balance_sum in groups:
            key = self._make_group_key(fields, groupby_fields, group_by)
            result[key] = {
                "debit": debit_sum or 0.0,
                "credit": credit_sum or 0.0,
                "balance": balance_sum or 0.0,
            }
        return result

    def _compute_aging(self, account_ids, date_to, extra_domain, group_by):
        """Compute aging buckets for receivable/payable accounts."""
        MoveLine = self.env["account.move.line"]
        accounts = self.env["account.account"].browse(account_ids)

        # Only for receivable/payable
        aging_accounts = accounts.filtered(
            lambda a: a.account_type in ("asset_receivable", "liability_payable")
        )
        if not aging_accounts:
            return []

        if isinstance(date_to, str):
            ref_date = date_type.fromisoformat(date_to)
        else:
            ref_date = date_to

        domain = [
            ("account_id", "in", aging_accounts.ids),
            ("reconciled", "=", False),
            ("parent_state", "=", "posted"),
        ] + extra_domain

        lines = MoveLine.search(domain)

        # Bucket definitions
        buckets = [
            ("current", 0),
            ("1_30", 30),
            ("31_60", 60),
            ("61_90", 90),
            ("over_90", None),
        ]

        aging_rows = defaultdict(lambda: {b[0]: 0.0 for b in buckets})
        aging_rows.default_factory = lambda: {
            "current": 0.0,
            "1_30": 0.0,
            "31_60": 0.0,
            "61_90": 0.0,
            "over_90": 0.0,
            "total": 0.0,
        }

        for line in lines:
            due_date = line.date_maturity or line.date
            days_past = (ref_date - due_date).days

            if days_past <= 0:
                bucket = "current"
            elif days_past <= 30:
                bucket = "1_30"
            elif days_past <= 60:
                bucket = "31_60"
            elif days_past <= 90:
                bucket = "61_90"
            else:
                bucket = "over_90"

            key = self._make_line_group_key(line, group_by)
            aging_rows[key][bucket] += line.amount_residual
            aging_rows[key]["total"] += line.amount_residual

        result = []
        for key in sorted(aging_rows.keys()):
            row = {
                **self._format_group_key(key, group_by),
                **aging_rows[key],
            }
            result.append(row)
        return result

    def _get_groupby_fields(self, group_by):
        """Convert logical group_by names to ORM field names."""
        if "account_type" in group_by:
            # Group by account_type requires post-processing
            fields = ["account_id"]
            for gb in group_by:
                if gb not in ("account", "account_type"):
                    fields.append(GROUP_BY_FIELD_MAP[gb])
            return fields
        return [GROUP_BY_FIELD_MAP[gb] for gb in group_by]

    def _make_group_key(self, field_values, groupby_fields, group_by):
        """Build a hashable key from _read_group results."""
        key_parts = []
        field_idx = 0

        for gb in group_by:
            if gb == "account_type":
                # Get account_type from the account_id record
                account_rec = field_values[0]  # account_id is always first
                key_parts.append(
                    ("account_type", account_rec.account_type if account_rec else "")
                )
            elif gb == "account":
                rec = field_values[field_idx]
                key_parts.append(
                    ("account", rec.code if rec else "", rec.name if rec else "")
                )
                if "account_type" not in group_by:
                    field_idx += 1
            else:
                rec = field_values[field_idx]
                if gb == "partner":
                    key_parts.append(("partner", rec.name if rec else ""))
                elif gb == "journal":
                    key_parts.append(("journal", rec.code if rec else ""))
                elif gb == "currency":
                    key_parts.append(("currency", rec.name if rec else ""))
                field_idx += 1

            if (
                gb in ("account", "account_type")
                and "account_type" in group_by
                and "account" in group_by
            ):
                continue
            elif gb != "account_type":
                field_idx += 1

        return tuple(key_parts)

    def _make_line_group_key(self, line, group_by):
        """Build a key from a move line record."""
        key_parts = []
        for gb in group_by:
            if gb == "account":
                key_parts.append(
                    ("account", line.account_id.code, line.account_id.name)
                )
            elif gb == "account_type":
                key_parts.append(("account_type", line.account_id.account_type))
            elif gb == "partner":
                key_parts.append(("partner", line.partner_id.name or ""))
            elif gb == "journal":
                key_parts.append(("journal", line.journal_id.code))
            elif gb == "currency":
                key_parts.append(("currency", line.currency_id.name or ""))
        return tuple(key_parts)

    def _format_group_key(self, key, group_by):
        """Convert a group key tuple back to a readable dict."""
        result = {}
        for part in key:
            field_type = part[0]
            if field_type == "account":
                result["account_code"] = part[1]
                result["account_name"] = part[2]
            elif field_type == "account_type":
                result["account_type"] = part[1]
            elif field_type == "partner":
                result["partner_name"] = part[1]
            elif field_type == "journal":
                result["journal_code"] = part[1]
            elif field_type == "currency":
                result["currency"] = part[1]
        return result
