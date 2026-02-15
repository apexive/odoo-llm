"""Menu management tools: tree, find, create, update, delete"""

import logging
from typing import Optional

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.llm_tool.decorators import llm_tool

_logger = logging.getLogger(__name__)


class WebsiteToolMenu(models.Model):
    _name = "website.tool.menu"
    _inherit = "website.tool.mixin"
    _description = "LLM tools for website menu management"

    def _format_menu_tree(self, node):
        """Convert Odoo menu tree dict to a simpler structure."""
        fields = node.get("fields", {})
        result = {
            "id": fields.get("id"),
            "name": fields.get("name", ""),
            "url": fields.get("url", ""),
            "new_window": fields.get("new_window", False),
            "sequence": fields.get("sequence", 10),
            "is_mega_menu": fields.get("is_mega_menu", False),
            "children": [],
        }
        for child in node.get("children", []):
            result["children"].append(self._format_menu_tree(child))
        return result

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def website_get_menu_tree(
        self,
        website: Optional[str] = None,
    ) -> dict:
        """Get the full menu hierarchy of a website

        Returns the complete menu tree with all items and their children,
        organized by sequence.

        Args:
            website: Website name or ID (defaults to current website)

        Returns:
            Dictionary with menu tree structure
        """
        ws = self._resolve_website(website)
        tree = self.env["website.menu"].get_tree(ws.id)
        return {"menu_tree": self._format_menu_tree(tree)}

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def website_find_menus(
        self,
        name: Optional[str] = None,
        url: Optional[str] = None,
        website: Optional[str] = None,
        limit: int = 50,
    ) -> dict:
        """Search website menu items

        Find menu items matching the given criteria.

        Args:
            name: Menu name (partial match)
            url: Menu URL (partial match)
            website: Website name or ID (defaults to current website)
            limit: Maximum results (default: 50)

        Returns:
            Dictionary with matching menu items
        """
        ws = self._resolve_website(website)
        domain = [("website_id", "=", ws.id)]
        if name:
            domain.append(("name", "ilike", name))
        if url:
            domain.append(("url", "ilike", url))

        menus = self.env["website.menu"].search(
            domain, limit=limit, order="sequence, id"
        )

        result = []
        for menu in menus:
            result.append(
                {
                    "id": menu.id,
                    "name": menu.name,
                    "url": menu.url or "",
                    "new_window": menu.new_window,
                    "sequence": menu.sequence,
                    "parent": menu.parent_id.name if menu.parent_id else "",
                    "parent_id": menu.parent_id.id if menu.parent_id else 0,
                    "children_count": len(menu.child_id),
                    "is_mega_menu": menu.is_mega_menu,
                    "page_id": menu.page_id.id if menu.page_id else 0,
                    "page_url": menu.page_id.url if menu.page_id else "",
                    "is_visible": menu.is_visible,
                }
            )

        return {"menus": result, "count": len(result)}

    @llm_tool(destructive_hint=True)
    def website_create_menu(
        self,
        name: str,
        url: Optional[str] = None,
        website: Optional[str] = None,
        parent: Optional[str] = None,
        page: Optional[str] = None,
        sequence: int = 10,
        new_window: bool = False,
        is_mega_menu: bool = False,
        groups: Optional[str] = None,
    ) -> dict:
        """Create a new menu item

        Adds a new item to the website navigation menu.

        Args:
            name: Menu item display text
            url: URL the menu item links to (e.g. "/about",
                 "https://example.com"). Not needed if page is set.
            website: Website name or ID (defaults to current website)
            parent: Parent menu name or ID for submenu placement
            page: Page URL or name to link to (alternative to raw url)
            sequence: Display order (lower = earlier, default: 10)
            new_window: Open link in new browser tab (default: False)
            is_mega_menu: Create as mega menu (default: False)
            groups: Comma-separated group XML IDs for visibility restriction
                (e.g. "base.group_user,base.group_portal")

        Returns:
            Dictionary with created menu item details
        """
        ws = self._resolve_website(website)
        vals = {
            "name": name,
            "website_id": ws.id,
            "sequence": sequence,
            "new_window": new_window,
            "is_mega_menu": is_mega_menu,
        }

        if page:
            page_rec = self._resolve_page(page, ws)
            vals["page_id"] = page_rec.id
            vals["url"] = page_rec.url
        elif url:
            vals["url"] = url
        else:
            vals["url"] = ""

        if parent:
            parent_menu = self._resolve_menu(parent, ws)
            vals["parent_id"] = parent_menu.id

        if groups:
            vals["group_ids"] = [(6, 0, self._resolve_groups(groups).ids)]

        menu = self.env["website.menu"].create(vals)

        return {
            "id": menu.id,
            "name": menu.name,
            "url": menu.url,
            "sequence": menu.sequence,
            "parent": menu.parent_id.name if menu.parent_id else "",
            "is_mega_menu": menu.is_mega_menu,
            "message": f"Menu item '{name}' created",
        }

    @llm_tool(destructive_hint=True)
    def website_update_menu(
        self,
        menu: str,
        name: Optional[str] = None,
        url: Optional[str] = None,
        sequence: Optional[int] = None,
        parent: Optional[str] = None,
        new_window: Optional[bool] = None,
        page: Optional[str] = None,
        is_mega_menu: Optional[bool] = None,
        groups: Optional[str] = None,
        website: Optional[str] = None,
    ) -> dict:
        """Update a menu item

        Modify menu item properties like name, URL, position, or parent.

        Args:
            menu: Menu item name or ID to update
            name: New menu display text
            url: New URL
            sequence: New display order
            parent: New parent menu name or ID (for moving to submenu)
            new_window: Open in new tab
            page: Page URL or name to link to (sets both page_id and url)
            is_mega_menu: Toggle mega menu mode
            groups: Comma-separated group XML IDs for visibility restriction
                (e.g. "base.group_user"). Pass empty string to clear.
            website: Website name or ID (defaults to current website)

        Returns:
            Dictionary with updated menu item details
        """
        ws = self._resolve_website(website)
        menu_rec = self._resolve_menu(menu, ws)

        vals = {}
        if name is not None:
            vals["name"] = name
        if url is not None:
            vals["url"] = url
        if sequence is not None:
            vals["sequence"] = sequence
        if new_window is not None:
            vals["new_window"] = new_window
        if parent is not None:
            parent_menu = self._resolve_menu(parent, ws)
            vals["parent_id"] = parent_menu.id
        if page is not None:
            page_rec = self._resolve_page(page, ws)
            vals["page_id"] = page_rec.id
            vals["url"] = page_rec.url
        if is_mega_menu is not None:
            vals["is_mega_menu"] = is_mega_menu
        if groups is not None:
            if groups:
                vals["group_ids"] = [(6, 0, self._resolve_groups(groups).ids)]
            else:
                vals["group_ids"] = [(5, 0, 0)]

        if not vals:
            raise UserError(_("No fields to update"))

        menu_rec.write(vals)

        return {
            "id": menu_rec.id,
            "name": menu_rec.name,
            "url": menu_rec.url or "",
            "sequence": menu_rec.sequence,
            "parent": menu_rec.parent_id.name if menu_rec.parent_id else "",
            "is_mega_menu": menu_rec.is_mega_menu,
            "message": f"Menu item '{menu_rec.name}' updated",
        }

    @llm_tool(destructive_hint=True)
    def website_delete_menu(
        self,
        menu: str,
        website: Optional[str] = None,
    ) -> dict:
        """Delete a menu item and its children

        Permanently removes a menu item. If the item has submenus,
        they will also be deleted.

        Args:
            menu: Menu item name or ID to delete
            website: Website name or ID (defaults to current website)

        Returns:
            Dictionary with deletion result
        """
        ws = self._resolve_website(website)
        menu_rec = self._resolve_menu(menu, ws)
        menu_name = menu_rec.name
        children_count = len(menu_rec.child_id)
        menu_rec.unlink()

        msg = f"Menu item '{menu_name}' deleted"
        if children_count:
            msg += f" (with {children_count} children)"

        return {
            "name": menu_name,
            "children_deleted": children_count,
            "message": msg,
        }
