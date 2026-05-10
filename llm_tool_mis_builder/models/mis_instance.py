"""MIS Instance Tools - CRUD operations for report instances"""

import logging
from datetime import date
from typing import Optional

from odoo import _, fields, models
from odoo.exceptions import UserError

from odoo.addons.llm_tool.decorators import llm_tool

_logger = logging.getLogger(__name__)


class MisReportInstance(models.Model):
    """Inherit MIS Report Instance to add LLM tools for instance management"""

    _inherit = "mis.report.instance"

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def mis_instance_list(
        self,
        report_id: Optional[int] = None,
        include_temporary: bool = False,
        limit: int = 50,
    ) -> dict:
        """List MIS report instances

        Returns a list of report instances that can be executed to
        produce report data.

        Args:
            report_id: Filter by report template ID (optional)
            include_temporary: Include temporary instances (default: False)
            limit: Maximum number of instances to return (default: 50)

        Returns:
            Dictionary with list of instances and their configuration
        """
        domain = []
        if report_id:
            domain.append(("report_id", "=", report_id))
        if not include_temporary:
            domain.append(("temporary", "=", False))

        instances = self.search(domain, limit=limit, order="name")

        result = []
        for instance in instances:
            instance_data = {
                "id": instance.id,
                "name": instance.name,
                "report_id": instance.report_id.id,
                "report_name": instance.report_id.name,
                "comparison_mode": instance.comparison_mode,
                "target_move": instance.target_move,
                "period_count": len(instance.period_ids),
                "temporary": instance.temporary,
            }

            if instance.company_id:
                instance_data["company"] = instance.company_id.name
            elif instance.multi_company:
                instance_data["companies"] = instance.company_ids.mapped("name")

            if not instance.comparison_mode:
                instance_data["date_from"] = str(instance.date_from) if instance.date_from else None
                instance_data["date_to"] = str(instance.date_to) if instance.date_to else None

            result.append(instance_data)

        return {
            "instances": result,
            "total_count": len(result),
        }

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def mis_instance_get(
        self,
        instance_id: Optional[int] = None,
        instance_name: Optional[str] = None,
    ) -> dict:
        """Get detailed information about a MIS report instance

        Retrieves complete instance configuration including all periods
        and their settings.

        Args:
            instance_id: ID of the instance (preferred)
            instance_name: Name of the instance (alternative)

        Returns:
            Dictionary with complete instance configuration
        """
        if not instance_id and not instance_name:
            raise UserError(_("Either instance_id or instance_name must be provided"))

        if instance_id:
            instance = self.browse(instance_id)
            if not instance.exists():
                raise UserError(_("Instance with ID %s not found") % instance_id)
        else:
            instance = self.search([("name", "=", instance_name)], limit=1)
            if not instance:
                raise UserError(_("Instance with name '%s' not found") % instance_name)

        # Get periods
        periods = []
        for period in instance.period_ids:
            period_data = {
                "id": period.id,
                "name": period.name,
                "sequence": period.sequence,
                "source": period.source,
                "mode": period.mode,
                "valid": period.valid,
            }

            if period.mode == "fix":
                period_data["manual_date_from"] = str(period.manual_date_from) if period.manual_date_from else None
                period_data["manual_date_to"] = str(period.manual_date_to) if period.manual_date_to else None
            elif period.mode == "relative":
                period_data["type"] = period.type
                period_data["offset"] = period.offset
                period_data["duration"] = period.duration
                period_data["is_ytd"] = period.is_ytd

            # Computed dates
            period_data["date_from"] = str(period.date_from) if period.date_from else None
            period_data["date_to"] = str(period.date_to) if period.date_to else None

            # Source-specific fields
            if period.source == "sumcol":
                period_data["sum_columns"] = [
                    {"period_id": s.period_to_sum_id.id, "sign": s.sign}
                    for s in period.source_sumcol_ids
                ]
            elif period.source == "cmpcol":
                period_data["compare_from_id"] = period.source_cmpcol_from_id.id
                period_data["compare_to_id"] = period.source_cmpcol_to_id.id

            if period.analytic_domain and period.analytic_domain != "[]":
                period_data["analytic_domain"] = period.analytic_domain

            periods.append(period_data)

        result = {
            "id": instance.id,
            "name": instance.name,
            "report_id": instance.report_id.id,
            "report_name": instance.report_id.name,
            "comparison_mode": instance.comparison_mode,
            "target_move": instance.target_move,
            "temporary": instance.temporary,
            "pivot_date": str(instance.pivot_date) if instance.pivot_date else None,
            "periods": periods,
            "no_auto_expand_accounts": instance.no_auto_expand_accounts,
            "display_columns_description": instance.display_columns_description,
        }

        if not instance.comparison_mode:
            result["date_from"] = str(instance.date_from) if instance.date_from else None
            result["date_to"] = str(instance.date_to) if instance.date_to else None

        if instance.company_id:
            result["company_id"] = instance.company_id.id
            result["company_name"] = instance.company_id.name
        elif instance.multi_company:
            result["multi_company"] = True
            result["company_ids"] = instance.company_ids.ids
            result["company_names"] = instance.company_ids.mapped("name")

        if instance.analytic_domain and instance.analytic_domain != "[]":
            result["analytic_domain"] = instance.analytic_domain

        return result

    @llm_tool(destructive_hint=True)
    def mis_instance_create(
        self,
        report_id: int,
        name: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        target_move: str = "posted",
        company_id: Optional[int] = None,
        temporary: bool = True,
        comparison_mode: bool = False,
        pivot_date: Optional[str] = None,
    ) -> dict:
        """Create a new MIS report instance

        Creates an instance of a report template for execution. Use
        comparison_mode=False with date_from/date_to for simple reports,
        or comparison_mode=True with periods for comparisons.

        Args:
            report_id: ID of the report template
            name: Name for the instance
            date_from: Start date in YYYY-MM-DD format (for non-comparison mode)
            date_to: End date in YYYY-MM-DD format (for non-comparison mode)
            target_move: 'posted' for posted entries only, 'all' for all entries
            company_id: Company ID to filter data (optional, uses current if not set)
            temporary: If True, instance will be auto-cleaned (default: True)
            comparison_mode: If True, use periods for date ranges (default: False)
            pivot_date: Base date for relative periods in YYYY-MM-DD format

        Returns:
            Dictionary with created instance details
        """
        report = self.env["mis.report"].browse(report_id)
        if not report.exists():
            raise UserError(_("Report with ID %s not found") % report_id)

        if target_move not in ["posted", "all"]:
            raise UserError(_("target_move must be 'posted' or 'all'"))

        values = {
            "name": name,
            "report_id": report_id,
            "target_move": target_move,
            "temporary": temporary,
        }

        if company_id:
            company = self.env["res.company"].browse(company_id)
            if not company.exists():
                raise UserError(_("Company with ID %s not found") % company_id)
            values["company_id"] = company_id
        else:
            values["company_id"] = self.env.company.id

        if comparison_mode:
            # Comparison mode - will use periods
            values["date_from"] = False
            values["date_to"] = False
            if pivot_date:
                values["date"] = pivot_date
        else:
            # Simple mode - use date range
            if not date_from or not date_to:
                # Default to current month
                today = date.today()
                date_from = date_from or str(today.replace(day=1))
                date_to = date_to or str(today)

            values["date_from"] = date_from
            values["date_to"] = date_to
            # Create a default period
            values["period_ids"] = [(0, 0, {"name": "Default"})]

        instance = self.create(values)

        return {
            "id": instance.id,
            "name": instance.name,
            "report_id": report_id,
            "report_name": report.name,
            "comparison_mode": instance.comparison_mode,
            "temporary": temporary,
            "message": f"Instance '{name}' created successfully",
        }

    @llm_tool(destructive_hint=True)
    def mis_instance_update(
        self,
        instance_id: int,
        name: Optional[str] = None,
        target_move: Optional[str] = None,
        company_id: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        pivot_date: Optional[str] = None,
        analytic_domain: Optional[str] = None,
        no_auto_expand_accounts: Optional[bool] = None,
        display_columns_description: Optional[bool] = None,
    ) -> dict:
        """Update an existing MIS report instance

        Updates instance settings. To modify periods, use the period
        management tools.

        Args:
            instance_id: ID of the instance to update
            name: New name (optional)
            target_move: 'posted' or 'all' (optional)
            company_id: New company ID (optional)
            date_from: New start date for non-comparison mode (optional)
            date_to: New end date for non-comparison mode (optional)
            pivot_date: New pivot date for comparison mode (optional)
            analytic_domain: Domain to filter move lines (optional)
            no_auto_expand_accounts: Disable account expansion (optional)
            display_columns_description: Show date ranges in headers (optional)

        Returns:
            Dictionary with updated instance details
        """
        instance = self.browse(instance_id)
        if not instance.exists():
            raise UserError(_("Instance with ID %s not found") % instance_id)

        values = {}

        if name is not None:
            values["name"] = name
        if target_move is not None:
            if target_move not in ["posted", "all"]:
                raise UserError(_("target_move must be 'posted' or 'all'"))
            values["target_move"] = target_move
        if company_id is not None:
            company = self.env["res.company"].browse(company_id)
            if not company.exists():
                raise UserError(_("Company with ID %s not found") % company_id)
            values["company_id"] = company_id
            values["multi_company"] = False
        if date_from is not None:
            values["date_from"] = date_from
        if date_to is not None:
            values["date_to"] = date_to
        if pivot_date is not None:
            values["date"] = pivot_date
        if analytic_domain is not None:
            values["analytic_domain"] = analytic_domain
        if no_auto_expand_accounts is not None:
            values["no_auto_expand_accounts"] = no_auto_expand_accounts
        if display_columns_description is not None:
            values["display_columns_description"] = display_columns_description

        if values:
            instance.write(values)

        return {
            "id": instance.id,
            "name": instance.name,
            "message": "Instance updated successfully",
        }

    @llm_tool(destructive_hint=True)
    def mis_instance_delete(self, instance_id: int) -> dict:
        """Delete a MIS report instance

        Permanently deletes an instance and all its periods.

        Args:
            instance_id: ID of the instance to delete

        Returns:
            Dictionary confirming deletion
        """
        instance = self.browse(instance_id)
        if not instance.exists():
            raise UserError(_("Instance with ID %s not found") % instance_id)

        name = instance.name
        instance.unlink()

        return {
            "message": f"Instance '{name}' deleted successfully",
            "deleted_id": instance_id,
        }

    @llm_tool(destructive_hint=True)
    def mis_instance_duplicate(
        self,
        instance_id: int,
        new_name: str,
        new_date_from: Optional[str] = None,
        new_date_to: Optional[str] = None,
    ) -> dict:
        """Duplicate a MIS report instance with optional date changes

        Creates a copy of an existing instance including all its
        periods and configuration.

        Args:
            instance_id: ID of the instance to duplicate
            new_name: Name for the new instance
            new_date_from: New start date (optional, for non-comparison mode)
            new_date_to: New end date (optional, for non-comparison mode)

        Returns:
            Dictionary with new instance details
        """
        instance = self.browse(instance_id)
        if not instance.exists():
            raise UserError(_("Instance with ID %s not found") % instance_id)

        values = {"name": new_name}
        if new_date_from:
            values["date_from"] = new_date_from
        if new_date_to:
            values["date_to"] = new_date_to

        new_instance = instance.copy(values)

        return {
            "id": new_instance.id,
            "name": new_instance.name,
            "original_id": instance_id,
            "original_name": instance.name,
            "period_count": len(new_instance.period_ids),
            "message": f"Instance duplicated as '{new_name}'",
        }
