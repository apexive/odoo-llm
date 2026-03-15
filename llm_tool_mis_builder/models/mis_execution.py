"""MIS Execution Tools - Report computation, analysis, and export"""

import json
import logging
from datetime import date, timedelta
from typing import Optional

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.llm_tool.decorators import llm_tool

_logger = logging.getLogger(__name__)


class MisReportInstance(models.Model):
    """Extend MIS Report Instance with execution and analysis tools"""

    _inherit = "mis.report.instance"

    @llm_tool(read_only_hint=True)
    def mis_report_compute(
        self,
        instance_id: int,
        pivot_date: Optional[str] = None,
    ) -> dict:
        """Execute a MIS report instance and get full results

        Computes all KPIs for all periods and returns the complete
        report data including values, styling, and drilldown info.

        Args:
            instance_id: ID of the report instance to compute
            pivot_date: Optional pivot date override in YYYY-MM-DD format

        Returns:
            Dictionary with complete report results including:
            - header: Column headers with labels and date ranges
            - rows: KPI rows with values for each column
            - notes: Cell annotations if user has access
        """
        instance = self.browse(instance_id)
        if not instance.exists():
            raise UserError(_("Instance with ID %s not found") % instance_id)

        # Apply pivot date if provided
        if pivot_date:
            instance = instance.with_context(mis_pivot_date=pivot_date)

        # Compute the report
        result = instance.compute()

        # Transform to more usable format
        cols = []
        for col in result.get("cols", []):
            cols.append({
                "key": col.get("col_key"),
                "label": col.get("label"),
                "description": col.get("description"),
                "colspan": col.get("colspan", 1),
            })

        rows = []
        for row in result.get("body", []):
            row_data = {
                "kpi_name": row.get("kpi_name"),
                "label": row.get("label"),
                "row_id": row.get("row_id"),
                "parent_row_id": row.get("parent_row_id"),
                "style": row.get("style"),
                "cells": [],
            }

            for cell in row.get("cells", []):
                cell_data = {
                    "val": cell.get("val"),
                    "val_rendered": cell.get("val_r"),
                    "val_comment": cell.get("val_c"),
                    "style": cell.get("style"),
                }
                if cell.get("drilldown_arg"):
                    cell_data["has_drilldown"] = True
                    cell_data["drilldown_arg"] = cell.get("drilldown_arg")
                row_data["cells"].append(cell_data)

            rows.append(row_data)

        return {
            "instance_id": instance_id,
            "instance_name": instance.name,
            "report_name": instance.report_id.name,
            "pivot_date": str(instance.pivot_date) if instance.pivot_date else None,
            "header": cols,
            "rows": rows,
            "notes": result.get("notes", {}),
        }

    @llm_tool(read_only_hint=True)
    def mis_report_preview(
        self,
        report_id: int,
        date_from: str,
        date_to: str,
        company_id: Optional[int] = None,
        target_move: str = "posted",
    ) -> dict:
        """Quick preview of a report template with ad-hoc date range

        Creates a temporary instance and computes the report for the
        specified date range. Useful for quick analysis without creating
        a permanent instance.

        Args:
            report_id: ID of the report template
            date_from: Start date in YYYY-MM-DD format
            date_to: End date in YYYY-MM-DD format
            company_id: Company ID (optional, uses current if not set)
            target_move: 'posted' or 'all' (default: 'posted')

        Returns:
            Dictionary with report results
        """
        report = self.env["mis.report"].browse(report_id)
        if not report.exists():
            raise UserError(_("Report with ID %s not found") % report_id)

        # Create temporary instance
        values = {
            "name": f"Preview - {report.name}",
            "report_id": report_id,
            "date_from": date_from,
            "date_to": date_to,
            "target_move": target_move,
            "temporary": True,
            "company_id": company_id or self.env.company.id,
            "period_ids": [(0, 0, {"name": "Preview"})],
        }

        instance = self.create(values)

        try:
            # Compute and return results
            result = instance.compute()

            # Transform results
            rows = []
            for row in result.get("body", []):
                if row.get("cells"):
                    cell = row["cells"][0]
                    rows.append({
                        "kpi_name": row.get("kpi_name"),
                        "label": row.get("label"),
                        "value": cell.get("val"),
                        "value_rendered": cell.get("val_r"),
                        "style": row.get("style"),
                    })

            return {
                "report_id": report_id,
                "report_name": report.name,
                "date_from": date_from,
                "date_to": date_to,
                "target_move": target_move,
                "rows": rows,
            }
        finally:
            # Clean up temporary instance
            instance.unlink()

    @llm_tool(read_only_hint=True)
    def mis_report_drilldown(
        self,
        instance_id: int,
        kpi_name: str,
        period_index: int,
        account_id: Optional[int] = None,
    ) -> dict:
        """Drill down into a specific cell to see underlying records

        Returns the move lines or other records that contribute to a
        specific KPI value in a specific period.

        Args:
            instance_id: ID of the report instance
            kpi_name: Name of the KPI row
            period_index: Index of the period column (0-based)
            account_id: Optional account ID for detail row drilldown

        Returns:
            Dictionary with drilldown action and record preview
        """
        instance = self.browse(instance_id)
        if not instance.exists():
            raise UserError(_("Instance with ID %s not found") % instance_id)

        # Find the KPI
        kpi = instance.report_id.kpi_ids.filtered(lambda k: k.name == kpi_name)
        if not kpi:
            raise UserError(_("KPI '%s' not found in report") % kpi_name)

        # Get the period
        periods = instance.period_ids.sorted("sequence")
        if period_index < 0 or period_index >= len(periods):
            raise UserError(
                _("Period index %s out of range (0-%s)")
                % (period_index, len(periods) - 1)
            )
        period = periods[period_index]

        # Build drilldown argument
        drilldown_arg = {
            "period_id": period.id,
            "expr": kpi.expression,
            "kpi_id": kpi.id,
        }
        if account_id:
            drilldown_arg["account_id"] = account_id

        # Get drilldown action
        action = instance.drilldown(drilldown_arg)

        if not action:
            return {
                "instance_id": instance_id,
                "kpi_name": kpi_name,
                "period": period.name,
                "message": "No drilldown available for this cell",
                "reason": "The KPI expression may not reference accounting data",
            }

        # Execute a limited search to preview records
        domain = action.get("domain", [])
        model = action.get("res_model")

        if model:
            records = self.env[model].search(domain, limit=20)
            preview = []
            for rec in records:
                rec_data = {"id": rec.id}
                if hasattr(rec, "name"):
                    rec_data["name"] = rec.name
                if hasattr(rec, "date"):
                    rec_data["date"] = str(rec.date) if rec.date else None
                if hasattr(rec, "debit"):
                    rec_data["debit"] = rec.debit
                if hasattr(rec, "credit"):
                    rec_data["credit"] = rec.credit
                if hasattr(rec, "balance"):
                    rec_data["balance"] = rec.balance
                if hasattr(rec, "account_id"):
                    rec_data["account"] = rec.account_id.display_name
                preview.append(rec_data)

            total_count = self.env[model].search_count(domain)
        else:
            preview = []
            total_count = 0

        return {
            "instance_id": instance_id,
            "kpi_name": kpi_name,
            "kpi_description": kpi.description,
            "period": period.name,
            "date_from": str(period.date_from) if period.date_from else None,
            "date_to": str(period.date_to) if period.date_to else None,
            "model": model,
            "domain": str(domain),
            "total_records": total_count,
            "preview_records": preview,
            "message": f"Found {total_count} records (showing first {len(preview)})",
        }

    @llm_tool(read_only_hint=True)
    def mis_report_export(
        self,
        instance_id: int,
        format: str = "json",
    ) -> dict:
        """Export report data to a structured format

        Computes the report and returns data in the specified format
        suitable for further processing or integration.

        Args:
            instance_id: ID of the report instance
            format: Export format - 'json' or 'csv' (default: 'json')

        Returns:
            Dictionary with exported data
        """
        instance = self.browse(instance_id)
        if not instance.exists():
            raise UserError(_("Instance with ID %s not found") % instance_id)

        if format not in ["json", "csv"]:
            raise UserError(_("Invalid format '%s'. Must be 'json' or 'csv'") % format)

        # Compute the report
        result = instance.compute()

        if format == "json":
            return {
                "instance_id": instance_id,
                "instance_name": instance.name,
                "report_name": instance.report_id.name,
                "format": "json",
                "data": result,
            }
        else:
            # CSV format - flatten to rows
            cols = result.get("cols", [])
            header = ["KPI", "Label"] + [c.get("label", "") for c in cols]

            rows = []
            for row in result.get("body", []):
                csv_row = [row.get("kpi_name", ""), row.get("label", "")]
                for cell in row.get("cells", []):
                    csv_row.append(cell.get("val_r", ""))
                rows.append(csv_row)

            return {
                "instance_id": instance_id,
                "instance_name": instance.name,
                "report_name": instance.report_id.name,
                "format": "csv",
                "header": header,
                "rows": rows,
            }

    @llm_tool(read_only_hint=True)
    def mis_compare_periods(
        self,
        report_id: int,
        periods: list,
        pivot_date: Optional[str] = None,
        company_id: Optional[int] = None,
        target_move: str = "posted",
    ) -> dict:
        """Compare KPIs across multiple time periods

        Creates a temporary multi-period instance and computes
        comparisons. Useful for YoY, MoM, or custom period analysis.

        Args:
            report_id: ID of the report template
            periods: List of period configurations, each with:
                - name: Column label
                - type: 'd', 'w', 'm', or 'y'
                - offset: Offset from pivot date (e.g., -1 for last period)
                - duration: Number of periods (default: 1)
            pivot_date: Base date in YYYY-MM-DD format (default: today)
            company_id: Company ID (optional)
            target_move: 'posted' or 'all' (default: 'posted')

        Returns:
            Dictionary with comparison results

        Example periods for YoY comparison:
            [
                {"name": "This Year", "type": "y", "offset": 0},
                {"name": "Last Year", "type": "y", "offset": -1},
            ]
        """
        report = self.env["mis.report"].browse(report_id)
        if not report.exists():
            raise UserError(_("Report with ID %s not found") % report_id)

        if not periods:
            raise UserError(_("At least one period configuration is required"))

        # Create temporary instance
        values = {
            "name": f"Comparison - {report.name}",
            "report_id": report_id,
            "target_move": target_move,
            "temporary": True,
            "company_id": company_id or self.env.company.id,
            "date": pivot_date or str(date.today()),
        }

        instance = self.create(values)

        try:
            # Create periods
            for seq, period_config in enumerate(periods, start=10):
                period_values = {
                    "report_instance_id": instance.id,
                    "name": period_config.get("name", f"Period {seq}"),
                    "source": "actuals",
                    "mode": "relative",
                    "type": period_config.get("type", "m"),
                    "offset": period_config.get("offset", 0),
                    "duration": period_config.get("duration", 1),
                    "is_ytd": period_config.get("is_ytd", False),
                    "sequence": seq,
                }
                self.env["mis.report.instance.period"].create(period_values)

            # Compute results
            result = instance.compute()

            # Transform for output
            cols = []
            for col in result.get("cols", []):
                cols.append({
                    "label": col.get("label"),
                    "description": col.get("description"),
                })

            rows = []
            for row in result.get("body", []):
                row_data = {
                    "kpi_name": row.get("kpi_name"),
                    "label": row.get("label"),
                    "values": [],
                }
                for cell in row.get("cells", []):
                    row_data["values"].append({
                        "value": cell.get("val"),
                        "rendered": cell.get("val_r"),
                    })
                rows.append(row_data)

            return {
                "report_id": report_id,
                "report_name": report.name,
                "pivot_date": str(instance.pivot_date),
                "columns": cols,
                "rows": rows,
            }
        finally:
            instance.unlink()

    @llm_tool(read_only_hint=True)
    def mis_kpi_trend(
        self,
        report_id: int,
        kpi_names: list,
        periods_back: int = 12,
        period_type: str = "m",
        company_id: Optional[int] = None,
    ) -> dict:
        """Get trend data for specific KPIs over time

        Computes KPI values over multiple historical periods to
        analyze trends and patterns.

        Args:
            report_id: ID of the report template
            kpi_names: List of KPI names to analyze
            periods_back: Number of periods to look back (default: 12)
            period_type: Period type - 'd', 'w', 'm', or 'y' (default: 'm')
            company_id: Company ID (optional)

        Returns:
            Dictionary with trend data for each KPI
        """
        report = self.env["mis.report"].browse(report_id)
        if not report.exists():
            raise UserError(_("Report with ID %s not found") % report_id)

        # Validate KPI names
        available_kpis = {kpi.name: kpi for kpi in report.kpi_ids}
        for kpi_name in kpi_names:
            if kpi_name not in available_kpis:
                raise UserError(_("KPI '%s' not found in report") % kpi_name)

        # Create temporary instance with historical periods
        values = {
            "name": f"Trend - {report.name}",
            "report_id": report_id,
            "target_move": "posted",
            "temporary": True,
            "company_id": company_id or self.env.company.id,
            "date": str(date.today()),
        }

        instance = self.create(values)

        try:
            # Create periods going back in time
            for i in range(periods_back - 1, -1, -1):
                offset = -i
                period_values = {
                    "report_instance_id": instance.id,
                    "name": f"Period {periods_back - i}",
                    "source": "actuals",
                    "mode": "relative",
                    "type": period_type,
                    "offset": offset,
                    "duration": 1,
                    "sequence": (periods_back - i) * 10,
                }
                self.env["mis.report.instance.period"].create(period_values)

            # Compute results
            result = instance.compute()

            # Extract trend data for requested KPIs
            trends = {}
            for kpi_name in kpi_names:
                trends[kpi_name] = {
                    "description": available_kpis[kpi_name].description,
                    "values": [],
                }

            for row in result.get("body", []):
                kpi_name = row.get("kpi_name")
                if kpi_name in kpi_names:
                    for i, cell in enumerate(row.get("cells", [])):
                        period = instance.period_ids.sorted("sequence")[i]
                        trends[kpi_name]["values"].append({
                            "period": period.name,
                            "date_from": str(period.date_from) if period.date_from else None,
                            "date_to": str(period.date_to) if period.date_to else None,
                            "value": cell.get("val"),
                            "rendered": cell.get("val_r"),
                        })

            return {
                "report_id": report_id,
                "report_name": report.name,
                "period_type": period_type,
                "periods_back": periods_back,
                "trends": trends,
            }
        finally:
            instance.unlink()

    @llm_tool(read_only_hint=True)
    def mis_account_breakdown(
        self,
        instance_id: int,
        kpi_name: str,
        period_index: int,
    ) -> dict:
        """Get account-level breakdown for a KPI

        Returns the individual account contributions to a KPI value,
        useful for detailed analysis when auto_expand_accounts is enabled.

        Args:
            instance_id: ID of the report instance
            kpi_name: Name of the KPI to break down
            period_index: Index of the period column (0-based)

        Returns:
            Dictionary with account-level breakdown
        """
        instance = self.browse(instance_id)
        if not instance.exists():
            raise UserError(_("Instance with ID %s not found") % instance_id)

        # Find the KPI
        kpi = instance.report_id.kpi_ids.filtered(lambda k: k.name == kpi_name)
        if not kpi:
            raise UserError(_("KPI '%s' not found in report") % kpi_name)

        if not kpi.auto_expand_accounts:
            return {
                "instance_id": instance_id,
                "kpi_name": kpi_name,
                "message": "KPI does not have auto_expand_accounts enabled",
                "accounts": [],
            }

        # Get the period
        periods = instance.period_ids.sorted("sequence")
        if period_index < 0 or period_index >= len(periods):
            raise UserError(
                _("Period index %s out of range (0-%s)")
                % (period_index, len(periods) - 1)
            )
        period = periods[period_index]

        # Compute the report to get account details
        result = instance.compute()

        # Find account detail rows for this KPI
        kpi_row_id = f"kpi_{kpi.id}"
        accounts = []

        for row in result.get("body", []):
            parent_id = row.get("parent_row_id")
            if parent_id == kpi_row_id:
                # This is a detail row
                if row.get("cells") and len(row["cells"]) > period_index:
                    cell = row["cells"][period_index]
                    accounts.append({
                        "label": row.get("label"),
                        "value": cell.get("val"),
                        "rendered": cell.get("val_r"),
                    })

        # Sort by absolute value
        accounts.sort(key=lambda x: abs(x.get("value") or 0), reverse=True)

        return {
            "instance_id": instance_id,
            "kpi_name": kpi_name,
            "kpi_description": kpi.description,
            "period": period.name,
            "date_from": str(period.date_from) if period.date_from else None,
            "date_to": str(period.date_to) if period.date_to else None,
            "account_count": len(accounts),
            "accounts": accounts,
        }

    @llm_tool(read_only_hint=True)
    def mis_variance_analysis(
        self,
        instance_id: int,
        base_period_index: int,
        compare_period_index: int,
        threshold_pct: float = 10.0,
    ) -> dict:
        """Analyze variance between two periods

        Identifies KPIs with significant changes between two periods,
        highlighting items that exceed the threshold percentage.

        Args:
            instance_id: ID of the report instance
            base_period_index: Index of the baseline period (0-based)
            compare_period_index: Index of the comparison period (0-based)
            threshold_pct: Minimum percentage change to report (default: 10.0)

        Returns:
            Dictionary with variance analysis results
        """
        instance = self.browse(instance_id)
        if not instance.exists():
            raise UserError(_("Instance with ID %s not found") % instance_id)

        periods = instance.period_ids.sorted("sequence")
        if base_period_index < 0 or base_period_index >= len(periods):
            raise UserError(_("Base period index out of range"))
        if compare_period_index < 0 or compare_period_index >= len(periods):
            raise UserError(_("Compare period index out of range"))

        base_period = periods[base_period_index]
        compare_period = periods[compare_period_index]

        # Compute the report
        result = instance.compute()

        # Analyze variances
        significant_changes = []
        all_variances = []

        for row in result.get("body", []):
            if not row.get("cells"):
                continue
            if row.get("parent_row_id"):
                continue  # Skip detail rows

            cells = row.get("cells", [])
            if len(cells) <= max(base_period_index, compare_period_index):
                continue

            base_val = cells[base_period_index].get("val")
            compare_val = cells[compare_period_index].get("val")

            # Skip non-numeric or None values
            if base_val is None or compare_val is None:
                continue
            try:
                base_val = float(base_val)
                compare_val = float(compare_val)
            except (TypeError, ValueError):
                continue

            # Calculate variance
            diff = compare_val - base_val
            if base_val != 0:
                pct_change = (diff / abs(base_val)) * 100
            else:
                pct_change = 100.0 if diff != 0 else 0.0

            variance_data = {
                "kpi_name": row.get("kpi_name"),
                "label": row.get("label"),
                "base_value": base_val,
                "compare_value": compare_val,
                "difference": diff,
                "pct_change": round(pct_change, 2),
            }
            all_variances.append(variance_data)

            if abs(pct_change) >= threshold_pct:
                significant_changes.append(variance_data)

        # Sort significant changes by absolute percentage change
        significant_changes.sort(key=lambda x: abs(x["pct_change"]), reverse=True)

        return {
            "instance_id": instance_id,
            "instance_name": instance.name,
            "base_period": {
                "name": base_period.name,
                "date_from": str(base_period.date_from) if base_period.date_from else None,
                "date_to": str(base_period.date_to) if base_period.date_to else None,
            },
            "compare_period": {
                "name": compare_period.name,
                "date_from": str(compare_period.date_from) if compare_period.date_from else None,
                "date_to": str(compare_period.date_to) if compare_period.date_to else None,
            },
            "threshold_pct": threshold_pct,
            "significant_changes_count": len(significant_changes),
            "total_kpis_analyzed": len(all_variances),
            "significant_changes": significant_changes,
        }
