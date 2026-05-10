"""Shared helpers for website LLM tools"""

import logging

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

REDIRECT_TYPES = {
    "permanent": "301",
    "temporary": "302",
    "rewrite": "308",
    "not_found": "404",
}

REDIRECT_TYPE_LABELS = {v: k for k, v in REDIRECT_TYPES.items()}

IMAGE_MIMETYPES = {
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/svg+xml",
    "image/webp",
}

MEDIA_TYPE_DOMAINS = {
    "image": [("mimetype", "=like", "image/%")],
    "document": [
        (
            "mimetype",
            "in",
            (
                "application/pdf",
                "application/msword",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/vnd.ms-excel",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
        )
    ],
    "video": [("mimetype", "=like", "video/%")],
}


class WebsiteToolMixin(models.AbstractModel):
    _name = "website.tool.mixin"
    _description = "Shared helpers for website LLM tools"

    def _resolve_website(self, identifier=None):
        """Resolve a website by name, ID, or None (current/first).

        Args:
            identifier: Website name (ilike), numeric ID, or None.

        Returns:
            website record (single)
        """
        Website = self.env["website"]
        if not identifier:
            return self._get_current_website()
        if isinstance(identifier, int) or (
            isinstance(identifier, str) and identifier.isdigit()
        ):
            website = Website.browse(int(identifier)).exists()
            if not website:
                raise UserError(_("Website with ID %s not found") % identifier)
            return website
        website = Website.search([("name", "ilike", identifier)], limit=1)
        if not website:
            raise UserError(_("Website '%s' not found") % identifier)
        return website

    def _resolve_page(self, identifier, website=None):
        """Resolve a page by URL (starts with /) or name.

        Args:
            identifier: Page URL (exact match) or name (ilike).
            website: Website record to scope search. Defaults to current.

        Returns:
            website.page record (single)
        """
        if website is None:
            website = self._get_current_website()
        Page = self.env["website.page"]
        domain = website.website_domain()
        if identifier.startswith("/"):
            page = Page.search(domain + [("url", "=", identifier)], limit=1)
        else:
            page = Page.search(domain + [("name", "ilike", identifier)], limit=1)
        if not page:
            raise UserError(_("Page '%s' not found") % identifier)
        return page

    def _resolve_menu(self, identifier, website=None):
        """Resolve a menu item by name or ID.

        Args:
            identifier: Menu name (ilike) or numeric ID.
            website: Website record to scope search. Defaults to current.

        Returns:
            website.menu record (single)
        """
        if website is None:
            website = self._get_current_website()
        Menu = self.env["website.menu"]
        if isinstance(identifier, int) or (
            isinstance(identifier, str) and identifier.isdigit()
        ):
            menu = Menu.browse(int(identifier)).exists()
            if not menu:
                raise UserError(_("Menu with ID %s not found") % identifier)
            if menu.website_id and menu.website_id != website:
                raise UserError(
                    _("Menu '%s' belongs to website '%s'")
                    % (menu.name, menu.website_id.name)
                )
            return menu
        menu = Menu.search(
            [("website_id", "=", website.id), ("name", "ilike", identifier)],
            limit=1,
        )
        if not menu:
            raise UserError(_("Menu '%s' not found") % identifier)
        return menu

    def _resolve_attachment(self, identifier):
        """Resolve an attachment by ID or name.

        Args:
            identifier: Attachment numeric ID or name (ilike).

        Returns:
            ir.attachment record (single)
        """
        Attachment = self.env["ir.attachment"]
        if isinstance(identifier, int) or (
            isinstance(identifier, str) and identifier.isdigit()
        ):
            att = Attachment.browse(int(identifier)).exists()
            if not att:
                raise UserError(_("Attachment with ID %s not found") % identifier)
            return att
        att = Attachment.search([("name", "ilike", identifier)], limit=1)
        if not att:
            raise UserError(_("Attachment '%s' not found") % identifier)
        return att

    def _resolve_groups(self, identifiers):
        """Resolve comma-separated group XML IDs to res.groups recordset.

        Args:
            identifiers: Comma-separated XML IDs (e.g. "base.group_user,base.group_portal")

        Returns:
            res.groups recordset
        """
        groups = self.env["res.groups"]
        for xml_id in identifiers.split(","):
            xml_id = xml_id.strip()
            if not xml_id:
                continue
            group = self.env.ref(xml_id, raise_if_not_found=False)
            if not group:
                raise UserError(_("Group '%s' not found") % xml_id)
            groups |= group
        return groups

    def _get_current_website(self):
        """Get the current website with fallback to first.

        Returns:
            website record (single)
        """
        Website = self.env["website"]
        try:
            website = Website.get_current_website()
        except Exception:
            website = Website.browse()
        if not website:
            website = Website.search([], limit=1)
        if not website:
            raise UserError(_("No website found"))
        return website
