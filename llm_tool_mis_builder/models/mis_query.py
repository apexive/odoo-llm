"""MIS Query Tools - CRUD operations for custom queries in report templates"""

import logging
from typing import Optional

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.llm_tool.decorators import llm_tool

_logger = logging.getLogger(__name__)


class MisReportQuery(models.Model):
    """Inherit MIS Report Query to add LLM tools for query management"""

    _inherit = "mis.report.query"

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def mis_query_list(self, report_id: int) -> dict:
        """List all custom queries defined in a MIS report template

        Returns the list of custom data queries that fetch non-accounting
        data for use in KPI expressions.

        Args:
            report_id: ID of the report template

        Returns:
            Dictionary with list of queries and their configuration
        """
        report = self.env["mis.report"].browse(report_id)
        if not report.exists():
            raise UserError(_("Report with ID %s not found") % report_id)

        queries = []
        for query in report.query_ids:
            queries.append({
                "id": query.id,
                "name": query.name,
                "model": query.model_id.model,
                "model_name": query.model_id.name,
                "field_names": query.field_names,
                "date_field": query.date_field.name,
                "domain": query.domain or "[]",
                "aggregate": query.aggregate,
                "has_company_filter": bool(query.company_field_id),
            })

        return {
            "report_id": report_id,
            "report_name": report.name,
            "queries": queries,
            "total_count": len(queries),
        }

    @llm_tool(destructive_hint=True)
    def mis_query_create(
        self,
        report_id: int,
        name: str,
        model: str,
        date_field: str,
        field_names: list,
        domain: str = "[]",
        aggregate: Optional[str] = None,
        company_field: Optional[str] = None,
    ) -> dict:
        """Create a new custom query in a MIS report template

        Adds a data query that fetches records from any Odoo model,
        making them available in KPI expressions.

        Args:
            report_id: ID of the report template
            name: Python variable name for the query (e.g., 'sales_data')
            model: Technical model name (e.g., 'sale.order')
            date_field: Field name for date filtering (e.g., 'date_order')
            field_names: List of field names to fetch (e.g., ['amount_total'])
            domain: Search domain as Python string (default: "[]")
            aggregate: Aggregation method - 'sum', 'avg', 'min', 'max', or None
            company_field: Field name for company filtering (optional)

        Returns:
            Dictionary with created query details

        Usage in KPIs:
            - Without aggregate: query returns list, use sum(q.field for q in query_name)
            - With aggregate='sum': query_name.field returns aggregated value
        """
        report = self.env["mis.report"].browse(report_id)
        if not report.exists():
            raise UserError(_("Report with ID %s not found") % report_id)

        # Find model
        model_rec = self.env["ir.model"].search([("model", "=", model)], limit=1)
        if not model_rec:
            raise UserError(_("Model '%s' not found") % model)

        # Find date field
        date_field_rec = self.env["ir.model.fields"].search([
            ("model_id", "=", model_rec.id),
            ("name", "=", date_field),
            ("ttype", "in", ("date", "datetime")),
        ], limit=1)
        if not date_field_rec:
            raise UserError(
                _("Date field '%s' not found on model '%s'") % (date_field, model)
            )

        # Find fields to fetch
        field_recs = self.env["ir.model.fields"].search([
            ("model_id", "=", model_rec.id),
            ("name", "in", field_names),
        ])
        if len(field_recs) != len(field_names):
            found = set(field_recs.mapped("name"))
            missing = set(field_names) - found
            raise UserError(
                _("Fields not found on model '%s': %s") % (model, ", ".join(missing))
            )

        # Validate aggregate
        if aggregate:
            valid_aggregates = ["sum", "avg", "min", "max"]
            if aggregate not in valid_aggregates:
                raise UserError(
                    _("Invalid aggregate '%s'. Must be one of: %s")
                    % (aggregate, ", ".join(valid_aggregates))
                )

        values = {
            "report_id": report_id,
            "name": name,
            "model_id": model_rec.id,
            "date_field": date_field_rec.id,
            "field_ids": [(6, 0, field_recs.ids)],
            "domain": domain,
            "aggregate": aggregate,
        }

        # Find company field if specified
        if company_field:
            company_field_rec = self.env["ir.model.fields"].search([
                ("model_id", "=", model_rec.id),
                ("name", "=", company_field),
            ], limit=1)
            if not company_field_rec:
                raise UserError(
                    _("Company field '%s' not found on model '%s'")
                    % (company_field, model)
                )
            values["company_field_id"] = company_field_rec.id

        query = self.create(values)

        return {
            "id": query.id,
            "name": query.name,
            "model": model,
            "field_names": query.field_names,
            "report_id": report_id,
            "message": f"Query '{name}' created successfully",
        }

    @llm_tool(destructive_hint=True)
    def mis_query_update(
        self,
        query_id: int,
        domain: Optional[str] = None,
        field_names: Optional[list] = None,
        aggregate: Optional[str] = None,
    ) -> dict:
        """Update an existing custom query

        Updates the configuration of a query. The model and date field
        cannot be changed after creation.

        Args:
            query_id: ID of the query to update
            domain: New search domain (optional)
            field_names: New list of fields to fetch (optional)
            aggregate: New aggregation method (optional, use empty string to remove)

        Returns:
            Dictionary with updated query details
        """
        query = self.browse(query_id)
        if not query.exists():
            raise UserError(_("Query with ID %s not found") % query_id)

        values = {}

        if domain is not None:
            values["domain"] = domain

        if field_names is not None:
            field_recs = self.env["ir.model.fields"].search([
                ("model_id", "=", query.model_id.id),
                ("name", "in", field_names),
            ])
            if len(field_recs) != len(field_names):
                found = set(field_recs.mapped("name"))
                missing = set(field_names) - found
                raise UserError(
                    _("Fields not found on model '%s': %s")
                    % (query.model_id.model, ", ".join(missing))
                )
            values["field_ids"] = [(6, 0, field_recs.ids)]

        if aggregate is not None:
            if aggregate:
                valid_aggregates = ["sum", "avg", "min", "max"]
                if aggregate not in valid_aggregates:
                    raise UserError(
                        _("Invalid aggregate '%s'. Must be one of: %s")
                        % (aggregate, ", ".join(valid_aggregates))
                    )
                values["aggregate"] = aggregate
            else:
                values["aggregate"] = False

        if values:
            query.write(values)

        return {
            "id": query.id,
            "name": query.name,
            "model": query.model_id.model,
            "field_names": query.field_names,
            "domain": query.domain or "[]",
            "aggregate": query.aggregate,
            "message": "Query updated successfully",
        }

    @llm_tool(destructive_hint=True)
    def mis_query_delete(self, query_id: int) -> dict:
        """Delete a custom query from a report template

        Permanently removes a query. KPIs that reference this query's
        name will fail to compute.

        Args:
            query_id: ID of the query to delete

        Returns:
            Dictionary confirming deletion
        """
        query = self.browse(query_id)
        if not query.exists():
            raise UserError(_("Query with ID %s not found") % query_id)

        name = query.name
        report_id = query.report_id.id
        query.unlink()

        return {
            "message": f"Query '{name}' deleted successfully",
            "deleted_id": query_id,
            "report_id": report_id,
        }
