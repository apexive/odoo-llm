"""Sales Order Tools - LLM tools for sales reporting and analysis"""

import logging
from datetime import datetime

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.llm_tool.decorators import llm_tool

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    """Inherit Sale Order to add LLM tools"""

    _inherit = "sale.order"

    @llm_tool(read_only_hint=True)
    def generate_sales_report(
        self, start_date: str, end_date: str, limit: int = 10
    ) -> dict:
        """Generate a sales summary report for a date range

        Provides statistics on sales orders including total revenue,
        order count, and top customers.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            limit: Maximum number of top customers to return (default: 10)

        Returns:
            Dictionary with sales statistics and top customers
        """
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError as e:
            raise UserError(_("Invalid date format. Use YYYY-MM-DD format.")) from e

        # Search for confirmed sales orders in date range
        orders = self.search(
            [
                ("date_order", ">=", start),
                ("date_order", "<=", end),
                ("state", "in", ["sale", "done"]),
            ]
        )

        if not orders:
            return {
                "start_date": start_date,
                "end_date": end_date,
                "total_orders": 0,
                "total_revenue": 0.0,
                "currency": self.env.company.currency_id.name,
                "top_customers": [],
            }

        # Calculate totals
        total_revenue = sum(orders.mapped("amount_total"))
        total_orders = len(orders)

        # Get top customers by revenue
        customer_revenue = {}
        for order in orders:
            partner = order.partner_id
            customer_revenue.setdefault(
                partner.id, {"name": partner.name, "revenue": 0.0, "order_count": 0}
            )
            customer_revenue[partner.id]["revenue"] += order.amount_total
            customer_revenue[partner.id]["order_count"] += 1

        # Sort by revenue and get top N
        top_customers = sorted(
            customer_revenue.values(), key=lambda x: x["revenue"], reverse=True
        )[:limit]

        return {
            "start_date": start_date,
            "end_date": end_date,
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "average_order_value": total_revenue / total_orders if total_orders else 0,
            "currency": self.env.company.currency_id.name,
            "top_customers": top_customers,
        }
