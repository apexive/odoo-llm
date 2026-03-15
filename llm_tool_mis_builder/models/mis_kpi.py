"""MIS KPI Tools - CRUD operations for KPIs within report templates"""

import logging
from typing import Optional

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.llm_tool.decorators import llm_tool

_logger = logging.getLogger(__name__)


class MisReportKpi(models.Model):
    """Inherit MIS Report KPI to add LLM tools for KPI management"""

    _inherit = "mis.report.kpi"

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def mis_kpi_list(
        self,
        report_id: int,
        include_expressions: bool = True,
    ) -> dict:
        """List all KPIs for a MIS report template

        Returns the list of KPIs (rows) defined in a report template,
        including their expressions and configuration.

        Args:
            report_id: ID of the report template
            include_expressions: Include expression details (default: True)

        Returns:
            Dictionary with list of KPIs and their configuration
        """
        report = self.env["mis.report"].browse(report_id)
        if not report.exists():
            raise UserError(_("Report with ID %s not found") % report_id)

        kpis = []
        for kpi in report.kpi_ids:
            kpi_data = {
                "id": kpi.id,
                "name": kpi.name,
                "description": kpi.description,
                "sequence": kpi.sequence,
                "type": kpi.type,
                "compare_method": kpi.compare_method,
                "accumulation_method": kpi.accumulation_method,
                "multi": kpi.multi,
                "auto_expand_accounts": kpi.auto_expand_accounts,
            }

            if include_expressions:
                kpi_data["expression"] = kpi.expression
                if kpi.multi:
                    kpi_data["expressions"] = [
                        {
                            "id": expr.id,
                            "name": expr.name,
                            "subkpi": expr.subkpi_id.name if expr.subkpi_id else None,
                        }
                        for expr in kpi.expression_ids
                    ]

            if kpi.style_id:
                kpi_data["style"] = kpi.style_id.name
            if kpi.style_expression:
                kpi_data["style_expression"] = kpi.style_expression

            kpis.append(kpi_data)

        return {
            "report_id": report_id,
            "report_name": report.name,
            "kpis": kpis,
            "total_count": len(kpis),
        }

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def mis_kpi_get(
        self,
        kpi_id: Optional[int] = None,
        report_id: Optional[int] = None,
        kpi_name: Optional[str] = None,
    ) -> dict:
        """Get detailed information about a specific KPI

        Retrieves complete KPI configuration including expressions,
        styling, and settings.

        Args:
            kpi_id: ID of the KPI (preferred)
            report_id: ID of the report (required if using kpi_name)
            kpi_name: Name of the KPI within the report

        Returns:
            Dictionary with complete KPI details
        """
        if kpi_id:
            kpi = self.browse(kpi_id)
            if not kpi.exists():
                raise UserError(_("KPI with ID %s not found") % kpi_id)
        elif report_id and kpi_name:
            kpi = self.search([
                ("report_id", "=", report_id),
                ("name", "=", kpi_name),
            ], limit=1)
            if not kpi:
                raise UserError(
                    _("KPI '%s' not found in report %s") % (kpi_name, report_id)
                )
        else:
            raise UserError(
                _("Either kpi_id or both report_id and kpi_name must be provided")
            )

        expressions = []
        for expr in kpi.expression_ids:
            expressions.append({
                "id": expr.id,
                "expression": expr.name,
                "subkpi_id": expr.subkpi_id.id if expr.subkpi_id else None,
                "subkpi_name": expr.subkpi_id.name if expr.subkpi_id else None,
            })

        return {
            "id": kpi.id,
            "name": kpi.name,
            "description": kpi.description,
            "report_id": kpi.report_id.id,
            "report_name": kpi.report_id.name,
            "expression": kpi.expression,
            "expressions": expressions,
            "type": kpi.type,
            "type_display": dict(self._fields["type"].selection).get(kpi.type),
            "compare_method": kpi.compare_method,
            "accumulation_method": kpi.accumulation_method,
            "sequence": kpi.sequence,
            "multi": kpi.multi,
            "auto_expand_accounts": kpi.auto_expand_accounts,
            "style_id": kpi.style_id.id if kpi.style_id else None,
            "style_name": kpi.style_id.name if kpi.style_id else None,
            "style_expression": kpi.style_expression or None,
        }

    @llm_tool(destructive_hint=True)
    def mis_kpi_create(
        self,
        report_id: int,
        name: str,
        description: str,
        expression: str,
        kpi_type: str = "num",
        compare_method: str = "pct",
        accumulation_method: str = "sum",
        sequence: int = 100,
        auto_expand_accounts: bool = False,
        style_id: Optional[int] = None,
    ) -> dict:
        """Create a new KPI in a MIS report template

        Adds a new KPI (row) to a report template with the specified
        expression and configuration.

        Args:
            report_id: ID of the report template
            name: Python variable name for the KPI (e.g., 'revenue')
            description: Display label for the KPI (e.g., 'Total Revenue')
            expression: Accounting expression (e.g., 'bal[70]' for account 70)
            kpi_type: Value type - 'num' (numeric), 'pct' (percentage), 'str' (string)
            compare_method: Comparison method - 'diff', 'pct', or 'none'
            accumulation_method: How to accumulate values - 'sum', 'avg', or 'none'
            sequence: Display order (default: 100)
            auto_expand_accounts: Show account-level details (default: False)
            style_id: Optional style ID for the KPI row

        Returns:
            Dictionary with created KPI details

        Expression Examples:
            - bal[70]: Balance on account 70
            - bali[1%]: Initial balance on accounts starting with 1
            - bale[60,61]: Ending balance on accounts 60 and 61
            - credp[70]: Credit amount on account 70 for the period
            - revenue + expenses: Reference other KPIs by name
        """
        report = self.env["mis.report"].browse(report_id)
        if not report.exists():
            raise UserError(_("Report with ID %s not found") % report_id)

        # Validate type
        valid_types = ["num", "pct", "str"]
        if kpi_type not in valid_types:
            raise UserError(
                _("Invalid KPI type '%s'. Must be one of: %s")
                % (kpi_type, ", ".join(valid_types))
            )

        # Validate compare_method
        valid_compare = ["diff", "pct", "none"]
        if compare_method not in valid_compare:
            raise UserError(
                _("Invalid compare_method '%s'. Must be one of: %s")
                % (compare_method, ", ".join(valid_compare))
            )

        # Validate accumulation_method
        valid_accumulation = ["sum", "avg", "none"]
        if accumulation_method not in valid_accumulation:
            raise UserError(
                _("Invalid accumulation_method '%s'. Must be one of: %s")
                % (accumulation_method, ", ".join(valid_accumulation))
            )

        values = {
            "report_id": report_id,
            "name": name,
            "description": description,
            "expression": expression,
            "type": kpi_type,
            "compare_method": compare_method,
            "accumulation_method": accumulation_method,
            "sequence": sequence,
            "auto_expand_accounts": auto_expand_accounts,
        }

        if style_id:
            style = self.env["mis.report.style"].browse(style_id)
            if not style.exists():
                raise UserError(_("Style with ID %s not found") % style_id)
            values["style_id"] = style_id

        kpi = self.create(values)

        return {
            "id": kpi.id,
            "name": kpi.name,
            "description": kpi.description,
            "expression": kpi.expression,
            "report_id": report_id,
            "message": f"KPI '{description}' created successfully",
        }

    @llm_tool(destructive_hint=True)
    def mis_kpi_update(
        self,
        kpi_id: int,
        description: Optional[str] = None,
        expression: Optional[str] = None,
        kpi_type: Optional[str] = None,
        compare_method: Optional[str] = None,
        accumulation_method: Optional[str] = None,
        sequence: Optional[int] = None,
        auto_expand_accounts: Optional[bool] = None,
        style_id: Optional[int] = None,
        style_expression: Optional[str] = None,
    ) -> dict:
        """Update an existing KPI's configuration

        Updates the specified properties of a KPI. The KPI name cannot
        be changed as it may be referenced by other KPIs.

        Args:
            kpi_id: ID of the KPI to update
            description: New display label (optional)
            expression: New accounting expression (optional)
            kpi_type: New value type (optional)
            compare_method: New comparison method (optional)
            accumulation_method: New accumulation method (optional)
            sequence: New display order (optional)
            auto_expand_accounts: Enable/disable account details (optional)
            style_id: New style ID (optional, 0 to remove)
            style_expression: Dynamic style expression (optional)

        Returns:
            Dictionary with updated KPI details
        """
        kpi = self.browse(kpi_id)
        if not kpi.exists():
            raise UserError(_("KPI with ID %s not found") % kpi_id)

        values = {}

        if description is not None:
            values["description"] = description
        if expression is not None:
            values["expression"] = expression
        if kpi_type is not None:
            valid_types = ["num", "pct", "str"]
            if kpi_type not in valid_types:
                raise UserError(
                    _("Invalid KPI type '%s'. Must be one of: %s")
                    % (kpi_type, ", ".join(valid_types))
                )
            values["type"] = kpi_type
        if compare_method is not None:
            valid_compare = ["diff", "pct", "none"]
            if compare_method not in valid_compare:
                raise UserError(
                    _("Invalid compare_method '%s'. Must be one of: %s")
                    % (compare_method, ", ".join(valid_compare))
                )
            values["compare_method"] = compare_method
        if accumulation_method is not None:
            valid_accumulation = ["sum", "avg", "none"]
            if accumulation_method not in valid_accumulation:
                raise UserError(
                    _("Invalid accumulation_method '%s'. Must be one of: %s")
                    % (accumulation_method, ", ".join(valid_accumulation))
                )
            values["accumulation_method"] = accumulation_method
        if sequence is not None:
            values["sequence"] = sequence
        if auto_expand_accounts is not None:
            values["auto_expand_accounts"] = auto_expand_accounts
        if style_id is not None:
            if style_id:
                style = self.env["mis.report.style"].browse(style_id)
                if not style.exists():
                    raise UserError(_("Style with ID %s not found") % style_id)
            values["style_id"] = style_id if style_id else False
        if style_expression is not None:
            values["style_expression"] = style_expression

        if values:
            kpi.write(values)

        return {
            "id": kpi.id,
            "name": kpi.name,
            "description": kpi.description,
            "expression": kpi.expression,
            "message": "KPI updated successfully",
        }

    @llm_tool(destructive_hint=True)
    def mis_kpi_delete(self, kpi_id: int) -> dict:
        """Delete a KPI from a report template

        Permanently removes a KPI from its report template. Other KPIs
        that reference this KPI's name may break.

        Args:
            kpi_id: ID of the KPI to delete

        Returns:
            Dictionary confirming deletion
        """
        kpi = self.browse(kpi_id)
        if not kpi.exists():
            raise UserError(_("KPI with ID %s not found") % kpi_id)

        name = kpi.name
        description = kpi.description
        report_id = kpi.report_id.id
        kpi.unlink()

        return {
            "message": f"KPI '{description}' ({name}) deleted successfully",
            "deleted_id": kpi_id,
            "report_id": report_id,
        }

    @llm_tool(destructive_hint=True)
    def mis_kpi_reorder(
        self,
        report_id: int,
        kpi_order: list,
    ) -> dict:
        """Change the display order of KPIs in a report

        Reorders KPIs by assigning new sequence numbers based on their
        position in the provided list.

        Args:
            report_id: ID of the report template
            kpi_order: List of KPI IDs in desired order

        Returns:
            Dictionary confirming reorder
        """
        report = self.env["mis.report"].browse(report_id)
        if not report.exists():
            raise UserError(_("Report with ID %s not found") % report_id)

        # Validate all KPIs belong to the report
        report_kpi_ids = set(report.kpi_ids.ids)
        for kpi_id in kpi_order:
            if kpi_id not in report_kpi_ids:
                raise UserError(
                    _("KPI ID %s does not belong to report %s") % (kpi_id, report_id)
                )

        # Update sequences
        for sequence, kpi_id in enumerate(kpi_order, start=10):
            self.browse(kpi_id).write({"sequence": sequence})

        return {
            "report_id": report_id,
            "kpi_order": kpi_order,
            "message": f"Reordered {len(kpi_order)} KPIs",
        }
