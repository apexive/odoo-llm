"""MIS Period Tools - CRUD operations for report instance periods"""

import logging
from typing import Optional

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.llm_tool.decorators import llm_tool

_logger = logging.getLogger(__name__)


class MisReportInstancePeriod(models.Model):
    """Inherit MIS Report Instance Period to add LLM tools"""

    _inherit = "mis.report.instance.period"

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def mis_period_list(self, instance_id: int) -> dict:
        """List all periods (columns) for a MIS report instance

        Returns the list of periods/columns defined for an instance,
        including their date configuration and computed dates.

        Args:
            instance_id: ID of the report instance

        Returns:
            Dictionary with list of periods and their configuration
        """
        instance = self.env["mis.report.instance"].browse(instance_id)
        if not instance.exists():
            raise UserError(_("Instance with ID %s not found") % instance_id)

        periods = []
        for period in instance.period_ids:
            period_data = {
                "id": period.id,
                "name": period.name,
                "sequence": period.sequence,
                "source": period.source,
                "source_display": dict(self._fields["source"].selection).get(period.source),
                "mode": period.mode,
                "mode_display": dict(self._fields["mode"].selection).get(period.mode),
                "valid": period.valid,
                "date_from": str(period.date_from) if period.date_from else None,
                "date_to": str(period.date_to) if period.date_to else None,
            }

            if period.mode == "fix":
                period_data["manual_date_from"] = str(period.manual_date_from) if period.manual_date_from else None
                period_data["manual_date_to"] = str(period.manual_date_to) if period.manual_date_to else None
            elif period.mode == "relative":
                period_data["type"] = period.type
                period_data["type_display"] = dict(self._fields["type"].selection).get(period.type) if period.type else None
                period_data["offset"] = period.offset
                period_data["duration"] = period.duration
                period_data["is_ytd"] = period.is_ytd

            if period.source == "sumcol":
                period_data["sum_columns"] = [
                    {
                        "period_id": s.period_to_sum_id.id,
                        "period_name": s.period_to_sum_id.name,
                        "sign": s.sign,
                    }
                    for s in period.source_sumcol_ids
                ]
            elif period.source == "cmpcol":
                period_data["compare_from"] = {
                    "id": period.source_cmpcol_from_id.id,
                    "name": period.source_cmpcol_from_id.name,
                }
                period_data["compare_to"] = {
                    "id": period.source_cmpcol_to_id.id,
                    "name": period.source_cmpcol_to_id.name,
                }

            periods.append(period_data)

        return {
            "instance_id": instance_id,
            "instance_name": instance.name,
            "comparison_mode": instance.comparison_mode,
            "pivot_date": str(instance.pivot_date) if instance.pivot_date else None,
            "periods": periods,
            "total_count": len(periods),
        }

    @llm_tool(destructive_hint=True)
    def mis_period_create(
        self,
        instance_id: int,
        name: str,
        source: str = "actuals",
        mode: str = "relative",
        period_type: Optional[str] = None,
        offset: int = -1,
        duration: int = 1,
        is_ytd: bool = False,
        manual_date_from: Optional[str] = None,
        manual_date_to: Optional[str] = None,
        sequence: int = 100,
        analytic_domain: Optional[str] = None,
    ) -> dict:
        """Create a new period (column) in a MIS report instance

        Adds a period column to an instance. For actuals data, periods
        can use fixed dates or relative dates based on the pivot date.

        Args:
            instance_id: ID of the report instance
            name: Label for the column
            source: Data source - 'actuals', 'actuals_alt', 'sumcol', 'cmpcol'
            mode: Date mode - 'fix' (fixed dates), 'relative', or 'none'
            period_type: For relative mode - 'd' (day), 'w' (week), 'm' (month), 'y' (year)
            offset: For relative mode - offset from current period (default: -1 = last period)
            duration: For relative mode - number of periods to include (default: 1)
            is_ytd: For relative mode - year-to-date, forces start to Jan 1 (default: False)
            manual_date_from: For fixed mode - start date in YYYY-MM-DD format
            manual_date_to: For fixed mode - end date in YYYY-MM-DD format
            sequence: Display order (default: 100)
            analytic_domain: Additional domain to filter move lines (optional)

        Returns:
            Dictionary with created period details

        Examples:
            - Current month: mode='relative', period_type='m', offset=0
            - Last month: mode='relative', period_type='m', offset=-1
            - Same month last year: mode='relative', period_type='m', offset=-12
            - YTD: mode='relative', period_type='m', offset=0, is_ytd=True
            - Fixed Q1 2024: mode='fix', manual_date_from='2024-01-01', manual_date_to='2024-03-31'
        """
        instance = self.env["mis.report.instance"].browse(instance_id)
        if not instance.exists():
            raise UserError(_("Instance with ID %s not found") % instance_id)

        # Validate source
        valid_sources = ["actuals", "actuals_alt", "sumcol", "cmpcol"]
        if source not in valid_sources:
            raise UserError(
                _("Invalid source '%s'. Must be one of: %s")
                % (source, ", ".join(valid_sources))
            )

        # Validate mode
        valid_modes = ["fix", "relative", "none"]
        if mode not in valid_modes:
            raise UserError(
                _("Invalid mode '%s'. Must be one of: %s")
                % (mode, ", ".join(valid_modes))
            )

        # Source validation
        if source in ["actuals", "actuals_alt"] and mode == "none":
            raise UserError(_("Actuals sources require a date filter (mode cannot be 'none')"))
        if source in ["sumcol", "cmpcol"] and mode != "none":
            raise UserError(_("Sum and comparison columns must have mode='none'"))

        values = {
            "report_instance_id": instance_id,
            "name": name,
            "source": source,
            "mode": mode,
            "sequence": sequence,
        }

        if mode == "relative":
            if not period_type:
                raise UserError(_("period_type is required for relative mode"))
            valid_types = ["d", "w", "m", "y", "date_range"]
            if period_type not in valid_types:
                raise UserError(
                    _("Invalid period_type '%s'. Must be one of: %s")
                    % (period_type, ", ".join(valid_types))
                )
            values["type"] = period_type
            values["offset"] = offset
            values["duration"] = duration
            values["is_ytd"] = is_ytd
        elif mode == "fix":
            if not manual_date_from or not manual_date_to:
                raise UserError(_("manual_date_from and manual_date_to are required for fixed mode"))
            values["manual_date_from"] = manual_date_from
            values["manual_date_to"] = manual_date_to

        if analytic_domain:
            values["analytic_domain"] = analytic_domain

        period = self.create(values)

        return {
            "id": period.id,
            "name": period.name,
            "instance_id": instance_id,
            "date_from": str(period.date_from) if period.date_from else None,
            "date_to": str(period.date_to) if period.date_to else None,
            "valid": period.valid,
            "message": f"Period '{name}' created successfully",
        }

    @llm_tool(destructive_hint=True)
    def mis_period_update(
        self,
        period_id: int,
        name: Optional[str] = None,
        offset: Optional[int] = None,
        duration: Optional[int] = None,
        is_ytd: Optional[bool] = None,
        manual_date_from: Optional[str] = None,
        manual_date_to: Optional[str] = None,
        sequence: Optional[int] = None,
        analytic_domain: Optional[str] = None,
    ) -> dict:
        """Update an existing period's configuration

        Updates period settings. The source and mode cannot be changed
        after creation.

        Args:
            period_id: ID of the period to update
            name: New column label (optional)
            offset: New offset for relative mode (optional)
            duration: New duration for relative mode (optional)
            is_ytd: Enable/disable year-to-date (optional)
            manual_date_from: New start date for fixed mode (optional)
            manual_date_to: New end date for fixed mode (optional)
            sequence: New display order (optional)
            analytic_domain: New analytic domain filter (optional)

        Returns:
            Dictionary with updated period details
        """
        period = self.browse(period_id)
        if not period.exists():
            raise UserError(_("Period with ID %s not found") % period_id)

        values = {}

        if name is not None:
            values["name"] = name
        if offset is not None:
            values["offset"] = offset
        if duration is not None:
            values["duration"] = duration
        if is_ytd is not None:
            values["is_ytd"] = is_ytd
        if manual_date_from is not None:
            values["manual_date_from"] = manual_date_from
        if manual_date_to is not None:
            values["manual_date_to"] = manual_date_to
        if sequence is not None:
            values["sequence"] = sequence
        if analytic_domain is not None:
            values["analytic_domain"] = analytic_domain

        if values:
            period.write(values)

        return {
            "id": period.id,
            "name": period.name,
            "date_from": str(period.date_from) if period.date_from else None,
            "date_to": str(period.date_to) if period.date_to else None,
            "valid": period.valid,
            "message": "Period updated successfully",
        }

    @llm_tool(destructive_hint=True)
    def mis_period_delete(self, period_id: int) -> dict:
        """Delete a period from a report instance

        Permanently removes a period/column. Comparison and sum columns
        that reference this period may break.

        Args:
            period_id: ID of the period to delete

        Returns:
            Dictionary confirming deletion
        """
        period = self.browse(period_id)
        if not period.exists():
            raise UserError(_("Period with ID %s not found") % period_id)

        name = period.name
        instance_id = period.report_instance_id.id
        period.unlink()

        return {
            "message": f"Period '{name}' deleted successfully",
            "deleted_id": period_id,
            "instance_id": instance_id,
        }

    @llm_tool(destructive_hint=True)
    def mis_period_add_comparison(
        self,
        instance_id: int,
        name: str,
        from_period_id: int,
        to_period_id: int,
        sequence: int = 100,
    ) -> dict:
        """Add a comparison column between two periods

        Creates a column that compares values between two existing
        periods using the KPI's compare_method (diff, pct, or none).

        Args:
            instance_id: ID of the report instance
            name: Label for the comparison column (e.g., 'Variance', 'YoY Change')
            from_period_id: ID of the baseline period (denominator)
            to_period_id: ID of the period to compare (numerator)
            sequence: Display order (default: 100)

        Returns:
            Dictionary with created comparison period details
        """
        instance = self.env["mis.report.instance"].browse(instance_id)
        if not instance.exists():
            raise UserError(_("Instance with ID %s not found") % instance_id)

        from_period = self.browse(from_period_id)
        to_period = self.browse(to_period_id)

        if not from_period.exists():
            raise UserError(_("From period with ID %s not found") % from_period_id)
        if not to_period.exists():
            raise UserError(_("To period with ID %s not found") % to_period_id)

        # Validate periods belong to same instance
        if from_period.report_instance_id.id != instance_id:
            raise UserError(_("From period does not belong to this instance"))
        if to_period.report_instance_id.id != instance_id:
            raise UserError(_("To period does not belong to this instance"))

        period = self.create({
            "report_instance_id": instance_id,
            "name": name,
            "source": "cmpcol",
            "mode": "none",
            "source_cmpcol_from_id": from_period_id,
            "source_cmpcol_to_id": to_period_id,
            "sequence": sequence,
        })

        return {
            "id": period.id,
            "name": period.name,
            "instance_id": instance_id,
            "from_period": from_period.name,
            "to_period": to_period.name,
            "message": f"Comparison column '{name}' created successfully",
        }

    @llm_tool(destructive_hint=True)
    def mis_period_add_sum(
        self,
        instance_id: int,
        name: str,
        period_ids: list,
        signs: Optional[list] = None,
        sequence: int = 100,
        sum_account_details: bool = False,
    ) -> dict:
        """Add a sum column combining multiple periods

        Creates a column that sums values from multiple periods with
        optional signs for subtraction.

        Args:
            instance_id: ID of the report instance
            name: Label for the sum column (e.g., 'Total', 'Full Year')
            period_ids: List of period IDs to sum
            signs: List of signs ('+' or '-') for each period (default: all '+')
            sequence: Display order (default: 100)
            sum_account_details: Also sum account detail rows (default: False)

        Returns:
            Dictionary with created sum period details
        """
        instance = self.env["mis.report.instance"].browse(instance_id)
        if not instance.exists():
            raise UserError(_("Instance with ID %s not found") % instance_id)

        if not period_ids:
            raise UserError(_("At least one period_id is required"))

        # Default signs to all positive
        if signs is None:
            signs = ["+"] * len(period_ids)
        elif len(signs) != len(period_ids):
            raise UserError(_("signs list must have same length as period_ids"))

        # Validate signs
        for sign in signs:
            if sign not in ["+", "-"]:
                raise UserError(_("Invalid sign '%s'. Must be '+' or '-'") % sign)

        # Validate all periods exist and belong to instance
        periods = self.browse(period_ids)
        for period_id in period_ids:
            period = self.browse(period_id)
            if not period.exists():
                raise UserError(_("Period with ID %s not found") % period_id)
            if period.report_instance_id.id != instance_id:
                raise UserError(
                    _("Period %s does not belong to this instance") % period.name
                )

        # Create sum column
        sum_period = self.create({
            "report_instance_id": instance_id,
            "name": name,
            "source": "sumcol",
            "mode": "none",
            "source_sumcol_accdet": sum_account_details,
            "sequence": sequence,
        })

        # Create sum relationships
        sum_model = self.env["mis.report.instance.period.sum"]
        for period_id, sign in zip(period_ids, signs):
            sum_model.create({
                "period_id": sum_period.id,
                "period_to_sum_id": period_id,
                "sign": sign,
            })

        return {
            "id": sum_period.id,
            "name": sum_period.name,
            "instance_id": instance_id,
            "periods_summed": len(period_ids),
            "message": f"Sum column '{name}' created successfully",
        }
