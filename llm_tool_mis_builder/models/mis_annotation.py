"""MIS Annotation Tools - Cell annotation management"""

import logging
from typing import Optional

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.llm_tool.decorators import llm_tool

_logger = logging.getLogger(__name__)


class MisReportInstanceAnnotation(models.Model):
    """Inherit MIS Report Instance Annotation to add LLM tools"""

    _inherit = "mis.report.instance.annotation"

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def mis_annotation_list(self, instance_id: int) -> dict:
        """List all annotations for a MIS report instance

        Returns all cell annotations/notes for the specified instance.

        Args:
            instance_id: ID of the report instance

        Returns:
            Dictionary with list of annotations
        """
        instance = self.env["mis.report.instance"].browse(instance_id)
        if not instance.exists():
            raise UserError(_("Instance with ID %s not found") % instance_id)

        if not instance.user_can_read_annotation:
            return {
                "instance_id": instance_id,
                "message": "You do not have permission to read annotations",
                "annotations": [],
            }

        annotations = self.search([
            ("period_id", "in", instance.period_ids.ids),
        ])

        result = []
        for annotation in annotations:
            result.append({
                "id": annotation.id,
                "kpi_id": annotation.kpi_id.id,
                "kpi_name": annotation.kpi_id.name,
                "kpi_description": annotation.kpi_id.description,
                "period_id": annotation.period_id.id,
                "period_name": annotation.period_id.name,
                "subkpi_id": annotation.subkpi_id.id if annotation.subkpi_id else None,
                "subkpi_name": annotation.subkpi_id.name if annotation.subkpi_id else None,
                "note": annotation.note,
            })

        return {
            "instance_id": instance_id,
            "instance_name": instance.name,
            "annotations": result,
            "total_count": len(result),
        }

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def mis_annotation_get(
        self,
        instance_id: int,
        kpi_name: str,
        period_index: int,
        subkpi_name: Optional[str] = None,
    ) -> dict:
        """Get annotation for a specific cell

        Retrieves the annotation/note for a specific KPI and period
        combination.

        Args:
            instance_id: ID of the report instance
            kpi_name: Name of the KPI row
            period_index: Index of the period column (0-based)
            subkpi_name: Name of the subkpi for multi-valued KPIs (optional)

        Returns:
            Dictionary with annotation details or empty if none exists
        """
        instance = self.env["mis.report.instance"].browse(instance_id)
        if not instance.exists():
            raise UserError(_("Instance with ID %s not found") % instance_id)

        if not instance.user_can_read_annotation:
            return {
                "instance_id": instance_id,
                "message": "You do not have permission to read annotations",
            }

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

        # Find subkpi if specified
        subkpi = None
        if subkpi_name:
            subkpi = instance.report_id.subkpi_ids.filtered(
                lambda s: s.name == subkpi_name
            )
            if not subkpi:
                raise UserError(_("SubKPI '%s' not found in report") % subkpi_name)

        # Search for annotation
        domain = [
            ("period_id", "=", period.id),
            ("kpi_id", "=", kpi.id),
        ]
        if subkpi:
            domain.append(("subkpi_id", "=", subkpi.id))
        else:
            domain.append(("subkpi_id", "=", False))

        annotation = self.search(domain, limit=1)

        if annotation:
            return {
                "id": annotation.id,
                "instance_id": instance_id,
                "kpi_name": kpi_name,
                "kpi_description": kpi.description,
                "period_name": period.name,
                "subkpi_name": subkpi_name,
                "note": annotation.note,
                "has_annotation": True,
            }
        else:
            return {
                "instance_id": instance_id,
                "kpi_name": kpi_name,
                "kpi_description": kpi.description,
                "period_name": period.name,
                "subkpi_name": subkpi_name,
                "note": None,
                "has_annotation": False,
            }

    @llm_tool(destructive_hint=True)
    def mis_annotation_set(
        self,
        instance_id: int,
        kpi_name: str,
        period_index: int,
        note: str,
        subkpi_name: Optional[str] = None,
    ) -> dict:
        """Create or update an annotation for a specific cell

        Sets the annotation/note for a specific KPI and period cell.
        Creates a new annotation if none exists, updates if one exists.

        Args:
            instance_id: ID of the report instance
            kpi_name: Name of the KPI row
            period_index: Index of the period column (0-based)
            note: The annotation text to set
            subkpi_name: Name of the subkpi for multi-valued KPIs (optional)

        Returns:
            Dictionary confirming the annotation was set
        """
        instance = self.env["mis.report.instance"].browse(instance_id)
        if not instance.exists():
            raise UserError(_("Instance with ID %s not found") % instance_id)

        if not instance.user_can_edit_annotation:
            raise UserError(_("You do not have permission to edit annotations"))

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

        # Find subkpi if specified
        subkpi = None
        if subkpi_name:
            subkpi = instance.report_id.subkpi_ids.filtered(
                lambda s: s.name == subkpi_name
            )
            if not subkpi:
                raise UserError(_("SubKPI '%s' not found in report") % subkpi_name)

        # Search for existing annotation
        domain = [
            ("period_id", "=", period.id),
            ("kpi_id", "=", kpi.id),
        ]
        if subkpi:
            domain.append(("subkpi_id", "=", subkpi.id))
        else:
            domain.append(("subkpi_id", "=", False))

        annotation = self.search(domain, limit=1)

        if annotation:
            annotation.write({"note": note})
            action = "updated"
        else:
            values = {
                "period_id": period.id,
                "kpi_id": kpi.id,
                "note": note,
            }
            if subkpi:
                values["subkpi_id"] = subkpi.id
            annotation = self.create(values)
            action = "created"

        return {
            "id": annotation.id,
            "instance_id": instance_id,
            "kpi_name": kpi_name,
            "period_name": period.name,
            "subkpi_name": subkpi_name,
            "note": note,
            "action": action,
            "message": f"Annotation {action} successfully",
        }

    @llm_tool(destructive_hint=True)
    def mis_annotation_delete(self, annotation_id: int) -> dict:
        """Delete a cell annotation

        Permanently removes an annotation from a cell.

        Args:
            annotation_id: ID of the annotation to delete

        Returns:
            Dictionary confirming deletion
        """
        annotation = self.browse(annotation_id)
        if not annotation.exists():
            raise UserError(_("Annotation with ID %s not found") % annotation_id)

        instance = annotation.period_id.report_instance_id
        if not instance.user_can_edit_annotation:
            raise UserError(_("You do not have permission to delete annotations"))

        kpi_name = annotation.kpi_id.name
        period_name = annotation.period_id.name
        annotation.unlink()

        return {
            "message": f"Annotation for {kpi_name}/{period_name} deleted successfully",
            "deleted_id": annotation_id,
        }
