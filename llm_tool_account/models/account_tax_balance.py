"""Tax balance tools: summarize tax amounts by tax"""

import logging
from typing import Optional

from odoo import models

from odoo.addons.llm_tool.decorators import llm_tool

_logger = logging.getLogger(__name__)

TAX_GROUP_BY_FIELD = {
    "tax": "tax_line_id",
    "partner": "partner_id",
    "journal": "journal_id",
}


class AccountTaxBalance(models.Model):
    _name = "account.tool.tax.balance"
    _inherit = "account.tool.mixin"
    _description = "LLM tools for tax balance reporting"

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def account_get_tax_balances(
        self,
        date_from: str,
        date_to: str,
        tax: Optional[str] = None,
        tax_group: Optional[str] = None,
        journal: Optional[str] = None,
        move_type: Optional[str] = None,
        target_move: str = "posted",
        group_by: Optional[list] = None,
    ) -> dict:
        """Get tax balance summary grouped by tax

        Returns base amount and tax amount for each tax in the period.
        Useful for VAT/GST reporting and tax return preparation.

        Args:
            date_from: Period start date (YYYY-MM-DD)
            date_to: Period end date (YYYY-MM-DD)
            tax: Filter by tax name (partial match, optional)
            tax_group: Filter by tax group name (partial match, optional)
            journal: Filter by journal code or name (optional)
            move_type: Filter by move type: "invoice", "bill", etc. (optional)
            target_move: "posted" (default) or "all" entries
            group_by: Grouping dimensions list. Options: "tax" (default),
                      "partner", "journal". Can combine, e.g. ["tax", "partner"]

        Returns:
            Dictionary with per-tax base and tax amounts
        """
        from .account_move_entry import MOVE_TYPE_MAP

        if group_by is None:
            group_by = ["tax"]

        domain = self._build_tax_domain(
            date_from, date_to, target_move, journal, move_type, MOVE_TYPE_MAP
        )

        # Build groupby fields — always include tax_line_id first
        groupby_fields = ["tax_line_id"]
        for gb in group_by:
            field = TAX_GROUP_BY_FIELD.get(gb, gb)
            if field not in groupby_fields:
                groupby_fields.append(field)

        groups = self.env["account.move.line"]._read_group(
            domain=domain,
            groupby=groupby_fields,
            aggregates=["balance:sum", "tax_base_amount:sum"],
        )

        rows = []
        totals = {"base_amount": 0.0, "tax_amount": 0.0}

        for *field_values, balance_sum, base_sum in groups:
            row = self._format_tax_row(
                field_values, balance_sum, base_sum, group_by, tax, tax_group
            )
            if row is None:
                continue
            rows.append(row)
            totals["base_amount"] += row["base_amount"]
            totals["tax_amount"] += row["tax_amount"]

        # Sort by tax name, then extra grouping fields
        sort_keys = ["tax_name"]
        if "partner" in group_by:
            sort_keys.append("partner_name")
        if "journal" in group_by:
            sort_keys.append("journal_code")
        rows.sort(key=lambda r: tuple(r.get(k, "") for k in sort_keys))

        return {
            "date_from": date_from,
            "date_to": date_to,
            "target_move": target_move,
            "group_by": group_by,
            "rows": rows,
            "totals": totals,
            "row_count": len(rows),
        }

    def _build_tax_domain(
        self, date_from, date_to, target_move, journal, move_type, move_type_map
    ):
        """Build search domain for tax balance lines."""
        domain = [
            ("tax_line_id", "!=", False),
            ("date", ">=", date_from),
            ("date", "<=", date_to),
        ]
        if target_move == "posted":
            domain.append(("parent_state", "=", "posted"))
        else:
            domain.append(("parent_state", "!=", "cancel"))
        if journal:
            domain.append(("journal_id", "=", self._resolve_journal(journal).id))
        if move_type:
            odoo_type = move_type_map.get(move_type, move_type)
            domain.append(("move_id.move_type", "=", odoo_type))
        return domain

    def _format_tax_row(
        self,
        field_values,
        balance_sum,
        base_sum,
        group_by,
        tax_filter,
        tax_group_filter,
    ):
        """Format a single tax balance row. Returns None if filtered out."""
        tax_rec = field_values[0]
        if not tax_rec:
            return None

        # Apply optional name filters
        if tax_filter and tax_filter.lower() not in tax_rec.name.lower():
            return None
        if tax_group_filter and (
            not tax_rec.tax_group_id
            or tax_group_filter.lower() not in tax_rec.tax_group_id.name.lower()
        ):
            return None

        row = {
            "tax_name": tax_rec.name,
            "tax_group": tax_rec.tax_group_id.name if tax_rec.tax_group_id else "",
            "type_tax_use": tax_rec.type_tax_use,
            "base_amount": base_sum or 0.0,
            "tax_amount": -(balance_sum or 0.0),
        }

        # Add extra grouping labels
        field_idx = 1
        for gb in group_by:
            if gb == "tax":
                continue
            rec = field_values[field_idx]
            if gb == "partner":
                row["partner_name"] = rec.name if rec else ""
            elif gb == "journal":
                row["journal_code"] = rec.code if rec else ""
                row["journal_name"] = rec.name if rec else ""
            field_idx += 1

        return row
