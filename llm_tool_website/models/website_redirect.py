"""Redirect management tools: find, create, update, delete"""

import logging
from typing import Optional

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.llm_tool.decorators import llm_tool

_logger = logging.getLogger(__name__)


class WebsiteToolRedirect(models.Model):
    _name = "website.tool.redirect"
    _inherit = "website.tool.mixin"
    _description = "LLM tools for website redirect management"

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def website_find_redirects(
        self,
        url_from: Optional[str] = None,
        url_to: Optional[str] = None,
        redirect_type: Optional[str] = None,
        website: Optional[str] = None,
        limit: int = 50,
    ) -> dict:
        """Search URL redirect rules

        Find redirect rules by source URL, target URL, or type.

        Args:
            url_from: Source URL pattern (partial match)
            url_to: Target URL pattern (partial match)
            redirect_type: Type filter: "permanent" (301),
                "temporary" (302), "rewrite" (308), or "not_found" (404)
            website: Website name or ID (defaults to current website)
            limit: Maximum results (default: 50)

        Returns:
            Dictionary with matching redirect rules
        """
        from .website_tool_mixin import REDIRECT_TYPE_LABELS, REDIRECT_TYPES

        ws = self._resolve_website(website)
        domain = [("website_id", "in", (False, ws.id))]

        if url_from:
            domain.append(("url_from", "ilike", url_from))
        if url_to:
            domain.append(("url_to", "ilike", url_to))
        if redirect_type:
            odoo_type = REDIRECT_TYPES.get(redirect_type, redirect_type)
            domain.append(("redirect_type", "=", odoo_type))

        redirects = self.env["website.rewrite"].search(
            domain, limit=limit, order="sequence, id"
        )

        result = []
        for redir in redirects:
            result.append(
                {
                    "id": redir.id,
                    "name": redir.name,
                    "url_from": redir.url_from or "",
                    "url_to": redir.url_to or "",
                    "redirect_type": REDIRECT_TYPE_LABELS.get(
                        redir.redirect_type, redir.redirect_type
                    ),
                    "redirect_code": redir.redirect_type,
                    "active": redir.active,
                }
            )

        return {"redirects": result, "count": len(result)}

    @llm_tool(destructive_hint=True)
    def website_create_redirect(
        self,
        name: str,
        url_from: str,
        url_to: str,
        redirect_type: str = "permanent",
        website: Optional[str] = None,
    ) -> dict:
        """Create a URL redirect rule

        Sets up a redirect from one URL to another. Use for handling
        moved pages, URL restructuring, or vanity URLs.

        Args:
            name: Descriptive name for the redirect rule
            url_from: Source URL to redirect from (e.g. "/old-page")
            url_to: Target URL to redirect to (e.g. "/new-page")
            redirect_type: Type of redirect: "permanent" (301, cached by
                browsers), "temporary" (302, not cached),
                "rewrite" (308, both URLs accessible),
                or "not_found" (404, removes from routing).
                Default: "permanent"
            website: Website name or ID (defaults to current website)

        Returns:
            Dictionary with created redirect details
        """
        from .website_tool_mixin import REDIRECT_TYPES

        ws = self._resolve_website(website)
        odoo_type = REDIRECT_TYPES.get(redirect_type)
        if not odoo_type:
            raise UserError(
                _("Invalid redirect_type '%s'. Use: %s")
                % (redirect_type, ", ".join(REDIRECT_TYPES.keys()))
            )

        redir = self.env["website.rewrite"].create(
            {
                "name": name,
                "url_from": url_from,
                "url_to": url_to,
                "redirect_type": odoo_type,
                "website_id": ws.id,
            }
        )

        return {
            "id": redir.id,
            "name": redir.name,
            "url_from": redir.url_from,
            "url_to": redir.url_to,
            "redirect_type": redirect_type,
            "redirect_code": odoo_type,
            "message": (
                f"Redirect '{name}' created: " f"{url_from} -> {url_to} ({odoo_type})"
            ),
        }

    @llm_tool(destructive_hint=True)
    def website_update_redirect(
        self,
        redirect_id: int,
        name: Optional[str] = None,
        url_from: Optional[str] = None,
        url_to: Optional[str] = None,
        redirect_type: Optional[str] = None,
        active: Optional[bool] = None,
    ) -> dict:
        """Update a redirect rule

        Modify an existing redirect rule's properties.

        Args:
            redirect_id: ID of the redirect rule to update
            name: New descriptive name
            url_from: New source URL
            url_to: New target URL
            redirect_type: New type: "permanent", "temporary", "rewrite",
                or "not_found"
            active: Enable or disable the redirect rule

        Returns:
            Dictionary with updated redirect details
        """
        from .website_tool_mixin import REDIRECT_TYPE_LABELS, REDIRECT_TYPES

        redir = self.env["website.rewrite"].browse(redirect_id).exists()
        if not redir:
            raise UserError(_("Redirect with ID %s not found") % redirect_id)

        vals = {}
        if name is not None:
            vals["name"] = name
        if url_from is not None:
            vals["url_from"] = url_from
        if url_to is not None:
            vals["url_to"] = url_to
        if redirect_type is not None:
            odoo_type = REDIRECT_TYPES.get(redirect_type)
            if not odoo_type:
                raise UserError(
                    _("Invalid redirect_type '%s'. Use: %s")
                    % (redirect_type, ", ".join(REDIRECT_TYPES.keys()))
                )
            vals["redirect_type"] = odoo_type
        if active is not None:
            vals["active"] = active

        if not vals:
            raise UserError(_("No fields to update"))

        redir.write(vals)

        return {
            "id": redir.id,
            "name": redir.name,
            "url_from": redir.url_from or "",
            "url_to": redir.url_to or "",
            "redirect_type": REDIRECT_TYPE_LABELS.get(
                redir.redirect_type, redir.redirect_type
            ),
            "redirect_code": redir.redirect_type,
            "active": redir.active,
            "message": f"Redirect '{redir.name}' updated",
        }

    @llm_tool(destructive_hint=True)
    def website_delete_redirect(
        self,
        redirect_id: int,
    ) -> dict:
        """Delete a redirect rule

        Permanently removes a URL redirect rule.

        Args:
            redirect_id: ID of the redirect rule to delete

        Returns:
            Dictionary with deletion result
        """
        redir = self.env["website.rewrite"].browse(redirect_id).exists()
        if not redir:
            raise UserError(_("Redirect with ID %s not found") % redirect_id)

        redir_name = redir.name
        redir.unlink()

        return {
            "name": redir_name,
            "message": f"Redirect '{redir_name}' deleted",
        }
