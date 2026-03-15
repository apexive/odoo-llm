"""Website configuration tools: list, get config, update config"""

import logging
from typing import Optional

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.llm_tool.decorators import llm_tool

_logger = logging.getLogger(__name__)


class WebsiteToolConfig(models.Model):
    _name = "website.tool.config"
    _inherit = "website.tool.mixin"
    _description = "LLM tools for website configuration"

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def website_list(self) -> dict:
        """List all websites

        Returns all configured websites with their name, domain,
        and company.

        Returns:
            Dictionary with all websites
        """
        websites = self.env["website"].search([], order="sequence, id")
        result = []
        for ws in websites:
            result.append(
                {
                    "id": ws.id,
                    "name": ws.name,
                    "domain": ws.domain or "",
                    "company": ws.company_id.name,
                    "default_lang": ws.default_lang_id.name,
                    "language_count": ws.language_count,
                    "homepage_url": ws.homepage_url or "/",
                }
            )

        return {"websites": result, "count": len(result)}

    @llm_tool(read_only_hint=True, idempotent_hint=True)
    def website_get_config(
        self,
        website: Optional[str] = None,
    ) -> dict:
        """Get full website configuration

        Returns all configuration settings for a website including
        languages, social media links, analytics, CDN, and cookies.

        Args:
            website: Website name or ID (defaults to current website)

        Returns:
            Dictionary with website configuration
        """
        ws = self._resolve_website(website)
        languages = []
        for lang in ws.language_ids:
            languages.append(
                {
                    "code": lang.code,
                    "name": lang.name,
                    "is_default": lang.id == ws.default_lang_id.id,
                }
            )

        return {
            "id": ws.id,
            "name": ws.name,
            "domain": ws.domain or "",
            "company": ws.company_id.name,
            "homepage_url": ws.homepage_url or "/",
            "languages": languages,
            "social": {
                "twitter": ws.social_twitter or "",
                "facebook": ws.social_facebook or "",
                "github": ws.social_github or "",
                "linkedin": ws.social_linkedin or "",
                "youtube": ws.social_youtube or "",
                "instagram": ws.social_instagram or "",
                "tiktok": ws.social_tiktok or "",
            },
            "analytics": {
                "google_analytics_key": ws.google_analytics_key or "",
                "google_search_console": ws.google_search_console or "",
                "plausible_shared_key": ws.plausible_shared_key or "",
                "plausible_site": ws.plausible_site or "",
            },
            "cdn": {
                "cdn_activated": ws.cdn_activated,
                "cdn_url": ws.cdn_url or "",
            },
            "cookies_bar": ws.cookies_bar,
            "has_favicon": bool(ws.favicon),
            "has_logo": bool(ws.logo),
            "robots_txt": ws.robots_txt or "",
            "custom_code_head": ws.custom_code_head or "",
            "custom_code_footer": ws.custom_code_footer or "",
            "google_maps_api_key": ws.google_maps_api_key or "",
            "block_third_party_domains": ws.block_third_party_domains,
            "auth_signup_uninvited": ws.auth_signup_uninvited or "",
        }

    @llm_tool(destructive_hint=True)
    def website_update_config(
        self,
        website: Optional[str] = None,
        name: Optional[str] = None,
        domain: Optional[str] = None,
        homepage_url: Optional[str] = None,
        social_twitter: Optional[str] = None,
        social_facebook: Optional[str] = None,
        social_github: Optional[str] = None,
        social_linkedin: Optional[str] = None,
        social_youtube: Optional[str] = None,
        social_instagram: Optional[str] = None,
        social_tiktok: Optional[str] = None,
        google_analytics_key: Optional[str] = None,
        cookies_bar: Optional[bool] = None,
        favicon: Optional[str] = None,
        logo: Optional[str] = None,
        robots_txt: Optional[str] = None,
        custom_code_head: Optional[str] = None,
        custom_code_footer: Optional[str] = None,
        google_maps_api_key: Optional[str] = None,
        block_third_party_domains: Optional[bool] = None,
        auth_signup_uninvited: Optional[str] = None,
    ) -> dict:
        """Update website configuration

        Modify website settings including name, domain, social media
        links, analytics, and cookie bar visibility.

        Args:
            website: Website name or ID (defaults to current website)
            name: New website name
            domain: New website domain (e.g. "https://www.example.com")
            homepage_url: New homepage URL path (e.g. "/shop")
            social_twitter: X/Twitter account URL
            social_facebook: Facebook page URL
            social_github: GitHub organization URL
            social_linkedin: LinkedIn page URL
            social_youtube: YouTube channel URL
            social_instagram: Instagram profile URL
            social_tiktok: TikTok profile URL
            google_analytics_key: Google Analytics measurement ID
            cookies_bar: Show cookie consent bar (True/False)
            favicon: Base64-encoded favicon image data
            logo: Base64-encoded logo image data
            robots_txt: Custom robots.txt content
            custom_code_head: Custom HTML code for <head> section
            custom_code_footer: Custom HTML code for end of <body>
            google_maps_api_key: Google Maps API key
            block_third_party_domains: Block third-party domain resources
            auth_signup_uninvited: Signup policy: "b2b" or "b2c"

        Returns:
            Dictionary with updated configuration
        """
        ws = self._resolve_website(website)
        vals = {}
        field_map = {
            "name": name,
            "domain": domain,
            "homepage_url": homepage_url,
            "social_twitter": social_twitter,
            "social_facebook": social_facebook,
            "social_github": social_github,
            "social_linkedin": social_linkedin,
            "social_youtube": social_youtube,
            "social_instagram": social_instagram,
            "social_tiktok": social_tiktok,
            "google_analytics_key": google_analytics_key,
            "cookies_bar": cookies_bar,
            "favicon": favicon,
            "logo": logo,
            "robots_txt": robots_txt,
            "custom_code_head": custom_code_head,
            "custom_code_footer": custom_code_footer,
            "google_maps_api_key": google_maps_api_key,
            "block_third_party_domains": block_third_party_domains,
            "auth_signup_uninvited": auth_signup_uninvited,
        }
        for field, value in field_map.items():
            if value is not None:
                vals[field] = value

        if not vals:
            raise UserError(_("No configuration fields to update"))

        ws.write(vals)

        return {
            "id": ws.id,
            "name": ws.name,
            "domain": ws.domain or "",
            "updated_fields": list(vals.keys()),
            "message": f"Website '{ws.name}' configuration updated",
        }
