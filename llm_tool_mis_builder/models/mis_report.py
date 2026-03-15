"""MIS Report Template Tools - CRUD operations for MIS report templates"""

import logging
from typing import Optional

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.llm_tool.decorators import llm_tool

_logger = logging.getLogger(__name__)


class MisReport(models.Model):
    """Inherit MIS Report to add LLM tools for template management"""

    _inherit = "mis.report"

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def mis_report_list(
        self,
        search: Optional[str] = None,
        limit: int = 50,
        include_kpi_count: bool = True,
    ) -> dict:
        """List all MIS report templates with summary information

        Returns a list of available MIS report templates that can be used
        to create report instances.

        Args:
            search: Optional search term to filter reports by name
            limit: Maximum number of reports to return (default: 50)
            include_kpi_count: Include count of KPIs in each report (default: True)

        Returns:
            Dictionary with list of report templates and metadata
        """
        domain = []
        if search:
            domain.append(("name", "ilike", search))

        reports = self.search(domain, limit=limit, order="name")

        result = []
        for report in reports:
            report_data = {
                "id": report.id,
                "name": report.name,
                "description": report.description or "",
            }
            if include_kpi_count:
                report_data["kpi_count"] = len(report.kpi_ids)
                report_data["query_count"] = len(report.query_ids)
                report_data["subkpi_count"] = len(report.subkpi_ids)
            result.append(report_data)

        return {
            "reports": result,
            "total_count": len(result),
        }

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def mis_report_get(
        self,
        report_id: Optional[int] = None,
        report_name: Optional[str] = None,
    ) -> dict:
        """Get detailed information about a MIS report template

        Retrieves complete template information including KPIs, queries,
        subkpis, and configuration details.

        Args:
            report_id: ID of the report template (preferred)
            report_name: Name of the report template (alternative to ID)

        Returns:
            Dictionary with complete report template details
        """
        if not report_id and not report_name:
            raise UserError(_("Either report_id or report_name must be provided"))

        if report_id:
            report = self.browse(report_id)
            if not report.exists():
                raise UserError(_("Report with ID %s not found") % report_id)
        else:
            report = self.search([("name", "=", report_name)], limit=1)
            if not report:
                raise UserError(_("Report with name '%s' not found") % report_name)

        # Get KPIs
        kpis = []
        for kpi in report.kpi_ids:
            kpi_data = {
                "id": kpi.id,
                "name": kpi.name,
                "description": kpi.description,
                "expression": kpi.expression,
                "type": kpi.type,
                "compare_method": kpi.compare_method,
                "accumulation_method": kpi.accumulation_method,
                "sequence": kpi.sequence,
                "multi": kpi.multi,
                "auto_expand_accounts": kpi.auto_expand_accounts,
            }
            if kpi.style_id:
                kpi_data["style"] = kpi.style_id.name
            kpis.append(kpi_data)

        # Get queries
        queries = []
        for query in report.query_ids:
            queries.append({
                "id": query.id,
                "name": query.name,
                "model": query.model_id.model,
                "field_names": query.field_names,
                "domain": query.domain or "[]",
                "aggregate": query.aggregate,
                "date_field": query.date_field.name,
            })

        # Get subkpis
        subkpis = []
        for subkpi in report.subkpi_ids:
            subkpis.append({
                "id": subkpi.id,
                "name": subkpi.name,
                "description": subkpi.description,
                "sequence": subkpi.sequence,
            })

        return {
            "id": report.id,
            "name": report.name,
            "description": report.description or "",
            "style": report.style_id.name if report.style_id else None,
            "move_lines_source": report.move_lines_source.model,
            "account_model": report.account_model,
            "kpis": kpis,
            "queries": queries,
            "subkpis": subkpis,
        }

    @llm_tool(destructive_hint=True)
    def mis_report_create(
        self,
        name: str,
        description: Optional[str] = None,
        style_id: Optional[int] = None,
    ) -> dict:
        """Create a new MIS report template

        Creates an empty report template that can then have KPIs and
        queries added to it.

        Args:
            name: Name for the new report template
            description: Optional description of the report
            style_id: Optional ID of a mis.report.style to use as default

        Returns:
            Dictionary with created report details
        """
        values = {"name": name}

        if description:
            values["description"] = description
        if style_id:
            style = self.env["mis.report.style"].browse(style_id)
            if not style.exists():
                raise UserError(_("Style with ID %s not found") % style_id)
            values["style_id"] = style_id

        report = self.create(values)

        return {
            "id": report.id,
            "name": report.name,
            "description": report.description or "",
            "message": f"Report '{name}' created successfully",
        }

    @llm_tool(destructive_hint=True)
    def mis_report_update(
        self,
        report_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        style_id: Optional[int] = None,
    ) -> dict:
        """Update an existing MIS report template

        Updates the basic properties of a report template. To modify KPIs
        or queries, use the dedicated tools.

        Args:
            report_id: ID of the report template to update
            name: New name for the report (optional)
            description: New description (optional)
            style_id: New default style ID (optional)

        Returns:
            Dictionary with updated report details
        """
        report = self.browse(report_id)
        if not report.exists():
            raise UserError(_("Report with ID %s not found") % report_id)

        values = {}
        if name is not None:
            values["name"] = name
        if description is not None:
            values["description"] = description
        if style_id is not None:
            if style_id:
                style = self.env["mis.report.style"].browse(style_id)
                if not style.exists():
                    raise UserError(_("Style with ID %s not found") % style_id)
            values["style_id"] = style_id if style_id else False

        if values:
            report.write(values)

        return {
            "id": report.id,
            "name": report.name,
            "description": report.description or "",
            "message": "Report updated successfully",
        }

    @llm_tool(destructive_hint=True)
    def mis_report_delete(self, report_id: int) -> dict:
        """Delete a MIS report template

        Permanently deletes a report template and all its KPIs and queries.
        This action cannot be undone.

        Args:
            report_id: ID of the report template to delete

        Returns:
            Dictionary confirming deletion
        """
        report = self.browse(report_id)
        if not report.exists():
            raise UserError(_("Report with ID %s not found") % report_id)

        name = report.name
        report.unlink()

        return {
            "message": f"Report '{name}' deleted successfully",
            "deleted_id": report_id,
        }

    @llm_tool(destructive_hint=True)
    def mis_report_duplicate(
        self,
        report_id: int,
        new_name: str,
    ) -> dict:
        """Duplicate a MIS report template with a new name

        Creates a copy of an existing report template including all its
        KPIs, queries, and subkpis.

        Args:
            report_id: ID of the report template to duplicate
            new_name: Name for the new report copy

        Returns:
            Dictionary with new report details
        """
        report = self.browse(report_id)
        if not report.exists():
            raise UserError(_("Report with ID %s not found") % report_id)

        new_report = report.copy({"name": new_name})

        return {
            "id": new_report.id,
            "name": new_report.name,
            "description": new_report.description or "",
            "original_id": report_id,
            "original_name": report.name,
            "kpi_count": len(new_report.kpi_ids),
            "query_count": len(new_report.query_ids),
            "message": f"Report duplicated as '{new_name}'",
        }
