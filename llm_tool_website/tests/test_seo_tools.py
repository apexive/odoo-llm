"""Tests for website SEO management tools"""

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestSeoTools(TransactionCase):
    """Test SEO get, update, and audit tools"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.seo_tools = cls.env["website.tool.seo"]
        cls.website = cls.env["website"].search([], limit=1)

        # Create a test page for SEO operations
        result = cls.website.new_page(name="SEO Test Page", add_menu=False)
        cls.test_page = cls.env["website.page"].browse(result["page_id"])

    def test_get_seo(self):
        """Test getting SEO metadata"""
        result = self.seo_tools.website_get_seo(page=self.test_page.url)
        self.assertEqual(result["page_id"], self.test_page.id)
        self.assertIn("meta_title", result)
        self.assertIn("meta_description", result)
        self.assertIn("meta_keywords", result)
        self.assertIn("og_image", result)
        self.assertIn("seo_name", result)
        self.assertIn("is_seo_optimized", result)
        self.assertIn("website_indexed", result)

    def test_get_seo_page_info(self):
        """Test that SEO result includes page info"""
        result = self.seo_tools.website_get_seo(page=self.test_page.url)
        self.assertEqual(result["page_name"], self.test_page.name)
        self.assertEqual(result["page_url"], self.test_page.url)

    def test_update_seo(self):
        """Test updating SEO metadata"""
        result = self.seo_tools.website_update_seo(
            page=self.test_page.url,
            meta_title="Test SEO Title",
            meta_description="Test SEO description for search engines.",
            meta_keywords="test, seo, odoo",
        )
        self.assertEqual(result["meta_title"], "Test SEO Title")
        self.assertEqual(
            result["meta_description"],
            "Test SEO description for search engines.",
        )
        self.assertEqual(result["meta_keywords"], "test, seo, odoo")
        self.assertIn("message", result)

    def test_update_seo_name(self):
        """Test updating seo_name"""
        result = self.seo_tools.website_update_seo(
            page=self.test_page.url,
            seo_name="test-seo-page",
        )
        self.assertEqual(result["seo_name"], "test-seo-page")

    def test_update_seo_no_fields_raises(self):
        """Test that updating with no SEO fields raises error"""
        with self.assertRaises(UserError):
            self.seo_tools.website_update_seo(page=self.test_page.url)

    def test_seo_audit(self):
        """Test SEO audit for missing metadata"""
        # Publish the test page so it shows up in audit
        self.test_page.is_published = True
        # Clear any previously set SEO data
        self.test_page.view_id.write(
            {
                "website_meta_title": False,
                "website_meta_description": False,
                "website_meta_keywords": False,
            }
        )

        result = self.seo_tools.website_seo_audit()
        self.assertIn("issues", result)
        self.assertIn("total_published_pages", result)
        self.assertIsInstance(result["issues"], list)
        self.assertGreater(result["total_published_pages"], 0)

    def test_seo_audit_finds_missing_fields(self):
        """Test that audit identifies specific missing fields"""
        self.test_page.is_published = True
        self.test_page.view_id.write(
            {
                "website_meta_title": False,
                "website_meta_description": False,
                "website_meta_keywords": False,
            }
        )

        result = self.seo_tools.website_seo_audit()
        # Find our test page in the issues
        page_issues = [i for i in result["issues"] if i["id"] == self.test_page.id]
        if page_issues:
            missing = page_issues[0]["missing"]
            self.assertIn("meta_title", missing)
            self.assertIn("meta_description", missing)
            self.assertIn("meta_keywords", missing)

    def test_seo_audit_respects_limit(self):
        """Test that audit respects the limit parameter"""
        result = self.seo_tools.website_seo_audit(limit=1)
        self.assertLessEqual(result["count"], 1)
