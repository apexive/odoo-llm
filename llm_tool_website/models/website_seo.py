"""SEO tools: get metadata, update metadata, audit"""

import logging
from typing import Optional

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.llm_tool.decorators import llm_tool

_logger = logging.getLogger(__name__)


class WebsiteToolSeo(models.Model):
    _name = "website.tool.seo"
    _inherit = "website.tool.mixin"
    _description = "LLM tools for website SEO management"

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def website_get_seo(
        self,
        page: str,
        website: Optional[str] = None,
    ) -> dict:
        """Get SEO metadata for a page

        Returns the meta title, description, keywords, OpenGraph image,
        and SEO optimization status for a specific page.

        Args:
            page: Page URL (e.g. "/about") or name
            website: Website name or ID (defaults to current website)

        Returns:
            Dictionary with SEO metadata
        """
        ws = self._resolve_website(website)
        page_rec = self._resolve_page(page, ws)
        view = page_rec.view_id

        return {
            "page_id": page_rec.id,
            "page_name": page_rec.name,
            "page_url": page_rec.url,
            "meta_title": view.website_meta_title or "",
            "meta_description": view.website_meta_description or "",
            "meta_keywords": view.website_meta_keywords or "",
            "og_image": view.website_meta_og_img or "",
            "seo_name": view.seo_name or "",
            "is_seo_optimized": view.is_seo_optimized,
            "website_indexed": page_rec.website_indexed,
        }

    @llm_tool(destructive_hint=True)
    def website_update_seo(
        self,
        page: str,
        meta_title: Optional[str] = None,
        meta_description: Optional[str] = None,
        meta_keywords: Optional[str] = None,
        seo_name: Optional[str] = None,
        website: Optional[str] = None,
    ) -> dict:
        """Update SEO metadata for a page

        Set the meta title, description, keywords, and SEO-friendly URL
        name for a page. These fields affect search engine results and
        social sharing.

        Args:
            page: Page URL (e.g. "/about") or name
            meta_title: Page title for search results
                (recommended: 50-60 chars)
            meta_description: Page description for search results
                (recommended: 150-160 chars)
            meta_keywords: Comma-separated keywords for search engines
            seo_name: SEO-friendly URL slug
            website: Website name or ID (defaults to current website)

        Returns:
            Dictionary with updated SEO metadata
        """
        ws = self._resolve_website(website)
        page_rec = self._resolve_page(page, ws)
        view = page_rec.view_id

        vals = {}
        if meta_title is not None:
            vals["website_meta_title"] = meta_title
        if meta_description is not None:
            vals["website_meta_description"] = meta_description
        if meta_keywords is not None:
            vals["website_meta_keywords"] = meta_keywords
        if seo_name is not None:
            vals["seo_name"] = seo_name

        if not vals:
            raise UserError(_("No SEO fields to update"))

        view.write(vals)

        return {
            "page_id": page_rec.id,
            "page_name": page_rec.name,
            "page_url": page_rec.url,
            "meta_title": view.website_meta_title or "",
            "meta_description": view.website_meta_description or "",
            "meta_keywords": view.website_meta_keywords or "",
            "seo_name": view.seo_name or "",
            "is_seo_optimized": view.is_seo_optimized,
            "message": f"SEO metadata updated for '{page_rec.name}'",
        }

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def website_seo_audit(
        self,
        website: Optional[str] = None,
        limit: int = 50,
    ) -> dict:
        """Audit pages for missing SEO metadata

        Lists published pages that have incomplete SEO metadata
        (missing meta title, description, or keywords).

        Args:
            website: Website name or ID (defaults to current website)
            limit: Maximum results (default: 50)

        Returns:
            Dictionary with pages needing SEO attention
        """
        ws = self._resolve_website(website)
        domain = ws.website_domain() + [("is_published", "=", True)]
        pages = self.env["website.page"].search(domain, order="url")

        issues = []
        for page in pages:
            view = page.view_id
            missing = []
            if not view.website_meta_title:
                missing.append("meta_title")
            if not view.website_meta_description:
                missing.append("meta_description")
            if not view.website_meta_keywords:
                missing.append("meta_keywords")
            if not page.website_indexed:
                missing.append("not_indexed")
            if missing:
                issues.append(
                    {
                        "id": page.id,
                        "name": page.name,
                        "url": page.url,
                        "missing": missing,
                    }
                )
                if len(issues) >= limit:
                    break

        return {
            "issues": issues,
            "count": len(issues),
            "total_published_pages": len(pages),
        }
