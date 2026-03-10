"""Media management tools: find, upload, info, delete"""

import base64
import logging
import mimetypes
from typing import Optional

import requests

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.llm_tool.decorators import llm_tool

from .website_tool_mixin import IMAGE_MIMETYPES, MEDIA_TYPE_DOMAINS

_logger = logging.getLogger(__name__)


class WebsiteToolMedia(models.Model):
    _name = "website.tool.media"
    _inherit = "website.tool.mixin"
    _description = "LLM tools for website media management"

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def website_find_media(
        self,
        name: Optional[str] = None,
        mimetype: Optional[str] = None,
        media_type: Optional[str] = None,
        website: Optional[str] = None,
        limit: int = 50,
    ) -> dict:
        """Search website media files (images, documents, videos)

        Find media attachments matching the given criteria.
        Use media_type for quick filtering: "image", "document", or "video".

        Args:
            name: File name (partial match)
            mimetype: Exact mimetype filter (e.g. "image/png")
            media_type: Shortcut filter: "image", "document", or "video"
            website: Website name or ID (defaults to current website)
            limit: Maximum results (default: 50)

        Returns:
            Dictionary with matching media files
        """
        ws = self._resolve_website(website)
        domain = ws.website_domain() + [("type", "=", "binary")]
        if name:
            domain.append(("name", "ilike", name))
        if mimetype:
            domain.append(("mimetype", "=", mimetype))
        if media_type and media_type in MEDIA_TYPE_DOMAINS:
            domain.extend(MEDIA_TYPE_DOMAINS[media_type])

        attachments = self.env["ir.attachment"].search(
            domain, limit=limit, order="create_date desc"
        )

        result = []
        for att in attachments:
            result.append(
                {
                    "id": att.id,
                    "name": att.name,
                    "mimetype": att.mimetype or "",
                    "url": f"/web/image/{att.id}/{att.name}",
                    "file_size": att.file_size,
                    "create_date": str(att.create_date) if att.create_date else "",
                }
            )

        return {"media": result, "count": len(result)}

    @llm_tool(destructive_hint=True)
    def website_upload_image_url(
        self,
        url: str,
        name: Optional[str] = None,
        website: Optional[str] = None,
    ) -> dict:
        """Upload an image to the website from a URL

        Downloads the image from the given URL and creates a website
        attachment. Only image mimetypes are accepted.

        Args:
            url: URL of the image to download
            name: File name (defaults to URL filename)
            website: Website name or ID (defaults to current website)

        Returns:
            Dictionary with uploaded image details
        """
        ws = self._resolve_website(website)

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise UserError(_("Failed to download image: %s") % str(exc)) from exc

        content_type = response.headers.get("Content-Type", "").split(";")[0].strip()
        guessed_type = mimetypes.guess_type(url)[0]
        detected_mimetype = content_type or guessed_type or ""

        if not detected_mimetype.startswith("image/"):
            raise UserError(
                _("URL does not point to an image (detected: %s)") % detected_mimetype
            )

        if not name:
            name = url.rsplit("/", 1)[-1].split("?")[0] or "image"

        attachment = self.env["ir.attachment"].create(
            {
                "name": name,
                "type": "binary",
                "datas": base64.b64encode(response.content),
                "mimetype": detected_mimetype,
                "public": True,
                "res_model": "ir.ui.view",
                "website_id": ws.id,
            }
        )

        return {
            "id": attachment.id,
            "name": attachment.name,
            "image_url": f"/web/image/{attachment.id}/{attachment.name}",
            "mimetype": attachment.mimetype,
            "file_size": attachment.file_size,
        }

    @llm_tool(destructive_hint=True)
    def website_upload_image_base64(
        self,
        data: str,
        name: str,
        mimetype: str = "image/png",
        website: Optional[str] = None,
    ) -> dict:
        """Upload an image to the website from base64 data

        Creates a website attachment from base64-encoded image data.
        Only image mimetypes are accepted.

        Args:
            data: Base64-encoded image data
            name: File name for the image
            mimetype: Image mimetype (default: "image/png")
            website: Website name or ID (defaults to current website)

        Returns:
            Dictionary with uploaded image details
        """
        if mimetype not in IMAGE_MIMETYPES:
            raise UserError(
                _("Invalid image mimetype '%s'. Allowed: %s")
                % (mimetype, ", ".join(sorted(IMAGE_MIMETYPES)))
            )

        ws = self._resolve_website(website)

        attachment = self.env["ir.attachment"].create(
            {
                "name": name,
                "type": "binary",
                "datas": data,
                "mimetype": mimetype,
                "public": True,
                "res_model": "ir.ui.view",
                "website_id": ws.id,
            }
        )

        return {
            "id": attachment.id,
            "name": attachment.name,
            "image_url": f"/web/image/{attachment.id}/{attachment.name}",
            "mimetype": attachment.mimetype,
            "file_size": attachment.file_size,
        }

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def website_get_media_info(
        self,
        attachment_id: int,
    ) -> dict:
        """Get detailed information about a media attachment

        Returns full details about a specific attachment by its ID.

        Args:
            attachment_id: ID of the attachment

        Returns:
            Dictionary with attachment details
        """
        att = self._resolve_attachment(attachment_id)
        return {
            "id": att.id,
            "name": att.name,
            "mimetype": att.mimetype or "",
            "url": f"/web/image/{att.id}/{att.name}",
            "file_size": att.file_size,
            "checksum": att.checksum or "",
            "create_date": str(att.create_date) if att.create_date else "",
            "website_id": att.website_id.id if att.website_id else 0,
        }

    @llm_tool(destructive_hint=True)
    def website_delete_media(
        self,
        attachment_id: int,
    ) -> dict:
        """Delete a media attachment

        Permanently removes a media file from the website.

        Args:
            attachment_id: ID of the attachment to delete

        Returns:
            Dictionary with deletion result
        """
        att = self._resolve_attachment(attachment_id)
        att_name = att.name
        att.unlink()

        return {
            "name": att_name,
            "message": f"Media '{att_name}' deleted",
        }
