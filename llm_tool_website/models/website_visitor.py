"""Visitor analytics tools: stats, find, detail (all read-only)"""

import logging
from typing import Optional

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.llm_tool.decorators import llm_tool

_logger = logging.getLogger(__name__)


class WebsiteToolVisitor(models.Model):
    _name = "website.tool.visitor"
    _inherit = "website.tool.mixin"
    _description = "LLM tools for website visitor analytics"

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def website_visitor_stats(
        self,
        website: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> dict:
        """Get aggregate visitor statistics

        Returns total visitors, connected visitors, and top visited
        pages for the given period.

        Args:
            website: Website name or ID (defaults to current website)
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)

        Returns:
            Dictionary with visitor statistics
        """
        ws = self._resolve_website(website)
        domain = [("website_id", "=", ws.id)]

        if date_from:
            domain.append(("create_date", ">=", date_from))
        if date_to:
            domain.append(("last_connection_datetime", "<=", date_to))

        Visitor = self.env["website.visitor"].sudo()
        visitors = Visitor.search(domain)

        total = len(visitors)
        connected = len(visitors.filtered("is_connected"))
        with_partner = len(visitors.filtered("partner_id"))

        # Top pages from tracks
        top_pages = []
        if visitors:
            Track = self.env["website.track"].sudo()
            page_groups = Track._read_group(
                domain=[
                    ("visitor_id", "in", visitors.ids),
                    ("page_id", "!=", False),
                ],
                groupby=["page_id"],
                aggregates=["__count"],
            )
            for page, count in sorted(page_groups, key=lambda x: x[1], reverse=True)[
                :10
            ]:
                top_pages.append(
                    {
                        "page": page.name,
                        "url": page.url,
                        "visits": count,
                    }
                )

        return {
            "total_visitors": total,
            "connected_visitors": connected,
            "identified_visitors": with_partner,
            "top_pages": top_pages,
        }

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def website_find_visitors(
        self,
        partner: Optional[str] = None,
        country: Optional[str] = None,
        is_connected: Optional[bool] = None,
        website: Optional[str] = None,
        limit: int = 50,
    ) -> dict:
        """Search website visitors

        Find visitors by partner, country, or connection status.

        Args:
            partner: Partner name (partial match)
            country: Country name or code
            is_connected: Filter by active connection (True = online now)
            website: Website name or ID (defaults to current website)
            limit: Maximum results (default: 50)

        Returns:
            Dictionary with matching visitors
        """
        ws = self._resolve_website(website)
        domain = [("website_id", "=", ws.id)]

        if partner:
            partners = self.env["res.partner"].search(
                [("name", "ilike", partner)], limit=100
            )
            domain.append(("partner_id", "in", partners.ids))
        if country:
            countries = self.env["res.country"].search(
                ["|", ("name", "ilike", country), ("code", "=ilike", country)],
                limit=10,
            )
            domain.append(("country_id", "in", countries.ids))

        Visitor = self.env["website.visitor"].sudo()
        visitors = Visitor.search(
            domain, limit=limit, order="last_connection_datetime desc"
        )

        if is_connected is not None:
            visitors = visitors.filtered(lambda v: v.is_connected == is_connected)

        result = []
        for visitor in visitors:
            result.append(
                {
                    "id": visitor.id,
                    "name": visitor.name or "Anonymous",
                    "partner": visitor.partner_id.name if visitor.partner_id else "",
                    "country": visitor.country_id.name if visitor.country_id else "",
                    "visit_count": visitor.visit_count,
                    "page_count": visitor.page_count,
                    "last_connection": str(visitor.last_connection_datetime)
                    if visitor.last_connection_datetime
                    else "",
                    "is_connected": visitor.is_connected,
                }
            )

        return {"visitors": result, "count": len(result)}

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def website_visitor_detail(
        self,
        visitor_id: int,
    ) -> dict:
        """Get detailed information about a specific visitor

        Returns full visitor details including partner info, visit
        history, and page view timeline.

        Args:
            visitor_id: ID of the visitor to look up

        Returns:
            Dictionary with detailed visitor information
        """
        Visitor = self.env["website.visitor"].sudo()
        visitor = Visitor.browse(visitor_id).exists()
        if not visitor:
            raise UserError(_("Visitor with ID %s not found") % visitor_id)

        # Get page visit history
        Track = self.env["website.track"].sudo()
        tracks = Track.search(
            [("visitor_id", "=", visitor.id)],
            order="create_date desc",
            limit=50,
        )
        page_history = []
        for track in tracks:
            page_history.append(
                {
                    "page": track.page_id.name if track.page_id else "",
                    "url": track.url or (track.page_id.url if track.page_id else ""),
                    "visited_at": str(track.create_date) if track.create_date else "",
                }
            )

        return {
            "id": visitor.id,
            "name": visitor.name or "Anonymous",
            "partner": visitor.partner_id.name if visitor.partner_id else "",
            "email": visitor.email or "",
            "country": visitor.country_id.name if visitor.country_id else "",
            "lang": visitor.lang_id.name if visitor.lang_id else "",
            "timezone": visitor.timezone or "",
            "visit_count": visitor.visit_count,
            "page_count": visitor.page_count,
            "first_connection": str(visitor.create_date) if visitor.create_date else "",
            "last_connection": str(visitor.last_connection_datetime)
            if visitor.last_connection_datetime
            else "",
            "is_connected": visitor.is_connected,
            "time_since_last_action": visitor.time_since_last_action or "",
            "page_history": page_history,
        }
