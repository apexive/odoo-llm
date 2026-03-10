"""Tests for website configuration tools"""

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestConfigTools(TransactionCase):
    """Test website list, get config, update config tools"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config_tools = cls.env["website.tool.config"]
        cls.website = cls.env["website"].search([], limit=1)

    def test_website_list(self):
        """Test listing all websites"""
        result = self.config_tools.website_list()
        self.assertIn("websites", result)
        self.assertGreater(result["count"], 0)

        ws = result["websites"][0]
        self.assertIn("id", ws)
        self.assertIn("name", ws)
        self.assertIn("company", ws)
        self.assertIn("default_lang", ws)
        self.assertIn("homepage_url", ws)

    def test_get_config(self):
        """Test getting website configuration"""
        result = self.config_tools.website_get_config()
        self.assertIn("id", result)
        self.assertIn("name", result)
        self.assertIn("social", result)
        self.assertIn("analytics", result)
        self.assertIn("cdn", result)
        self.assertIn("languages", result)
        self.assertIn("cookies_bar", result)

    def test_get_config_social_fields(self):
        """Test that social media fields are present"""
        result = self.config_tools.website_get_config()
        social = result["social"]
        for field in [
            "twitter",
            "facebook",
            "github",
            "linkedin",
            "youtube",
            "instagram",
            "tiktok",
        ]:
            self.assertIn(field, social)

    def test_get_config_analytics_fields(self):
        """Test that analytics fields are present"""
        result = self.config_tools.website_get_config()
        analytics = result["analytics"]
        self.assertIn("google_analytics_key", analytics)
        self.assertIn("google_search_console", analytics)

    def test_get_config_languages(self):
        """Test that language list is populated"""
        result = self.config_tools.website_get_config()
        self.assertIsInstance(result["languages"], list)
        self.assertGreater(len(result["languages"]), 0)
        lang = result["languages"][0]
        self.assertIn("code", lang)
        self.assertIn("name", lang)
        self.assertIn("is_default", lang)

    def test_update_config(self):
        """Test updating website configuration"""
        result = self.config_tools.website_update_config(
            social_twitter="https://x.com/test",
            cookies_bar=True,
        )
        self.assertIn("message", result)
        self.assertIn("social_twitter", result["updated_fields"])
        self.assertIn("cookies_bar", result["updated_fields"])

        # Verify changes
        self.website.invalidate_recordset()
        self.assertEqual(self.website.social_twitter, "https://x.com/test")
        self.assertTrue(self.website.cookies_bar)

    def test_update_config_name(self):
        """Test updating website name"""
        original_name = self.website.name
        result = self.config_tools.website_update_config(name="Test Website Name")
        self.assertIn("name", result["updated_fields"])

        # Restore original name
        self.website.write({"name": original_name})

    def test_update_config_no_fields_raises(self):
        """Test updating with no fields raises error"""
        with self.assertRaises(UserError):
            self.config_tools.website_update_config()

    def test_get_config_by_website_id(self):
        """Test getting config for specific website by ID"""
        result = self.config_tools.website_get_config(website=str(self.website.id))
        self.assertEqual(result["id"], self.website.id)
