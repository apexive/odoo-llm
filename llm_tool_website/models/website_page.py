"""Page management tools: find, create, update, publish, clone, delete"""

import logging
from typing import Optional

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.llm_tool.decorators import llm_tool

_logger = logging.getLogger(__name__)


class WebsiteToolPage(models.Model):
    _name = "website.tool.page"
    _inherit = "website.tool.mixin"
    _description = "LLM tools for website page management"

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def website_find_pages(
        self,
        name: Optional[str] = None,
        url: Optional[str] = None,
        is_published: Optional[bool] = None,
        website: Optional[str] = None,
        limit: int = 50,
    ) -> dict:
        """Search website pages by name, URL, or publish status

        Find pages matching the given criteria. All filters are optional
        and combined with AND logic.

        Args:
            name: Page name (partial match)
            url: Page URL pattern (partial match, e.g. "/about")
            is_published: Filter by publish status (True/False)
            website: Website name or ID (defaults to current website)
            limit: Maximum results (default: 50)

        Returns:
            Dictionary with matching pages
        """
        ws = self._resolve_website(website)
        domain = ws.website_domain()
        if name:
            domain.append(("name", "ilike", name))
        if url:
            domain.append(("url", "ilike", url))
        if is_published is not None:
            domain.append(("is_published", "=", is_published))

        pages = self.env["website.page"].search(domain, limit=limit, order="url")
        result = []
        for page in pages:
            result.append(
                {
                    "id": page.id,
                    "name": page.name,
                    "url": page.url,
                    "is_published": page.is_published,
                    "website_indexed": page.website_indexed,
                    "date_publish": str(page.date_publish) if page.date_publish else "",
                    "is_homepage": page.is_homepage,
                    "visibility": page.view_id.visibility or "public",
                    "header_overlay": page.header_overlay,
                }
            )

        return {"pages": result, "count": len(result)}

    @llm_tool(destructive_hint=True)
    def website_create_page(
        self,
        name: str,
        add_menu: bool = False,
        website: Optional[str] = None,
    ) -> dict:
        """Create a new website page

        Creates a blank page using Odoo's native new_page() method.
        Optionally adds a menu item linking to the page.

        Args:
            name: Page name (will also be used for URL slug)
            add_menu: Create a menu item for this page (default: False)
            website: Website name or ID (defaults to current website)

        Returns:
            Dictionary with created page details
        """
        ws = self._resolve_website(website)
        result = ws.new_page(name=name, add_menu=add_menu)

        page_id = result.get("page_id")
        if page_id:
            page = self.env["website.page"].browse(page_id)
        else:
            page = self.env["website.page"].search(
                [("url", "=", result.get("url"))], limit=1
            )

        return {
            "id": page.id if page else 0,
            "name": name,
            "url": result.get("url", ""),
            "view_id": result.get("view_id", 0),
            "menu_id": result.get("menu_id", 0),
            "message": f"Page '{name}' created at {result.get('url', '')}",
        }

    @llm_tool(destructive_hint=True)
    def website_update_page(
        self,
        page: str,
        name: Optional[str] = None,
        url: Optional[str] = None,
        website_indexed: Optional[bool] = None,
        date_publish: Optional[str] = None,
        header_visible: Optional[bool] = None,
        footer_visible: Optional[bool] = None,
        visibility: Optional[str] = None,
        header_overlay: Optional[bool] = None,
        header_color: Optional[str] = None,
        website: Optional[str] = None,
    ) -> dict:
        """Update page properties

        Modify page settings like name, URL, indexing, and header/footer
        visibility. Does not modify page HTML content.

        Args:
            page: Page URL (e.g. "/about") or name to identify the page
            name: New page name
            url: New page URL (will be slugified)
            website_indexed: Whether search engines should index this page
            date_publish: Scheduled publish date (YYYY-MM-DD HH:MM:SS)
            header_visible: Show website header on this page
            footer_visible: Show website footer on this page
            visibility: Page access: "public", "connected", "restricted_group",
                or "password"
            header_overlay: Overlay header on top of page content
            header_color: Header background color (CSS value)
            website: Website name or ID (defaults to current website)

        Returns:
            Dictionary with updated page details
        """
        ws = self._resolve_website(website)
        page_rec = self._resolve_page(page, ws)

        vals = {}
        view_vals = {}
        if name is not None:
            vals["name"] = name
        if url is not None:
            vals["url"] = url
        if website_indexed is not None:
            vals["website_indexed"] = website_indexed
        if date_publish is not None:
            vals["date_publish"] = date_publish
        if header_visible is not None:
            vals["header_visible"] = header_visible
        if footer_visible is not None:
            vals["footer_visible"] = footer_visible
        if header_overlay is not None:
            vals["header_overlay"] = header_overlay
        if header_color is not None:
            vals["header_color"] = header_color
        if visibility is not None:
            vis_value = "" if visibility == "public" else visibility
            view_vals["visibility"] = vis_value

        if not vals and not view_vals:
            raise UserError(_("No fields to update"))

        if vals:
            page_rec.write(vals)
        if view_vals:
            page_rec.view_id.write(view_vals)

        return {
            "id": page_rec.id,
            "name": page_rec.name,
            "url": page_rec.url,
            "is_published": page_rec.is_published,
            "message": f"Page '{page_rec.name}' updated",
        }

    @llm_tool(destructive_hint=True)
    def website_publish_page(
        self,
        page: str,
        publish: bool = True,
        website: Optional[str] = None,
    ) -> dict:
        """Publish or unpublish a website page

        Toggle the publish state of a page. Unpublished pages are only
        visible to website designers.

        Args:
            page: Page URL (e.g. "/about") or name to identify the page
            publish: True to publish, False to unpublish (default: True)
            website: Website name or ID (defaults to current website)

        Returns:
            Dictionary with publish result
        """
        ws = self._resolve_website(website)
        page_rec = self._resolve_page(page, ws)
        page_rec.is_published = publish
        action = "published" if publish else "unpublished"
        return {
            "id": page_rec.id,
            "name": page_rec.name,
            "url": page_rec.url,
            "is_published": page_rec.is_published,
            "message": f"Page '{page_rec.name}' {action}",
        }

    @llm_tool(destructive_hint=True)
    def website_clone_page(
        self,
        page: str,
        new_name: Optional[str] = None,
        clone_menu: bool = True,
        website: Optional[str] = None,
    ) -> dict:
        """Clone an existing page

        Creates a copy of a page with all its content. Optionally
        clones associated menu items as well.

        Args:
            page: Page URL (e.g. "/about") or name to identify the page
            new_name: Name for the cloned page (defaults to "Copy of <name>")
            clone_menu: Also clone associated menu items (default: True)
            website: Website name or ID (defaults to current website)

        Returns:
            Dictionary with cloned page details
        """
        ws = self._resolve_website(website)
        page_rec = self._resolve_page(page, ws)

        new_url = self.env["website.page"].clone_page(
            page_rec.id, page_name=new_name, clone_menu=clone_menu
        )

        new_page = self.env["website.page"].search(
            ws.website_domain() + [("url", "=", new_url)], limit=1
        )

        return {
            "id": new_page.id if new_page else 0,
            "name": new_page.name
            if new_page
            else (new_name or f"Copy of {page_rec.name}"),
            "url": new_url,
            "message": f"Page '{page_rec.name}' cloned to '{new_url}'",
        }

    @llm_tool(destructive_hint=True)
    def website_delete_page(
        self,
        page: str,
        website: Optional[str] = None,
    ) -> dict:
        """Delete a website page

        Permanently deletes a page and its associated view. Menu items
        pointing to this page will also be removed.

        Args:
            page: Page URL (e.g. "/about") or name to identify the page
            website: Website name or ID (defaults to current website)

        Returns:
            Dictionary with deletion result
        """
        ws = self._resolve_website(website)
        page_rec = self._resolve_page(page, ws)
        page_name = page_rec.name
        page_url = page_rec.url
        page_rec.unlink()

        return {
            "name": page_name,
            "url": page_url,
            "message": f"Page '{page_name}' ({page_url}) deleted",
        }
