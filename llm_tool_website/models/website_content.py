"""Page content tools: read and write page HTML"""

import logging
from typing import Optional

from odoo import models

from odoo.addons.llm_tool.decorators import llm_tool

_logger = logging.getLogger(__name__)


class WebsiteToolContent(models.Model):
    _name = "website.tool.content"
    _inherit = "website.tool.mixin"
    _description = "LLM tools for website page content"

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def website_get_page_content(
        self,
        page: str,
        website: Optional[str] = None,
    ) -> dict:
        """Get the HTML content of a website page

        Returns the raw arch (HTML/XML) of the page's underlying view.
        Use this to read what is actually rendered on the page.

        Args:
            page: Page URL (e.g. "/about") or name to identify the page
            website: Website name or ID (defaults to current website)

        Returns:
            Dictionary with page content and metadata
        """
        ws = self._resolve_website(website)
        page_rec = self._resolve_page(page, ws)

        return {
            "page_id": page_rec.id,
            "view_id": page_rec.view_id.id,
            "name": page_rec.name,
            "url": page_rec.url,
            "content": page_rec.view_id.arch or "",
        }

    @llm_tool(destructive_hint=True)
    def website_update_page_content(
        self,
        page: str,
        content: str,
        website: Optional[str] = None,
    ) -> dict:
        """Update the HTML content of a website page

        Writes new arch (HTML/XML) to the page's underlying view.
        This replaces the entire page body content.

        Args:
            page: Page URL (e.g. "/about") or name to identify the page
            content: New HTML/XML content for the page
            website: Website name or ID (defaults to current website)

        Returns:
            Dictionary with update result
        """
        ws = self._resolve_website(website)
        page_rec = self._resolve_page(page, ws)
        page_rec.view_id.arch = content

        return {
            "page_id": page_rec.id,
            "view_id": page_rec.view_id.id,
            "name": page_rec.name,
            "url": page_rec.url,
            "message": f"Content of page '{page_rec.name}' updated",
        }
