"""Tests for website tool mixin resolver methods"""

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestWebsiteToolMixin(TransactionCase):
    """Test shared resolver methods in WebsiteToolMixin"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mixin = cls.env["website.tool.mixin"]
        cls.website = cls.env["website"].search([], limit=1)

    def test_get_current_website(self):
        """Test getting current website with fallback"""
        website = self.mixin._get_current_website()
        self.assertTrue(website)

    def test_resolve_website_none(self):
        """Test resolving website with None returns current"""
        website = self.mixin._resolve_website(None)
        self.assertTrue(website)

    def test_resolve_website_by_id(self):
        """Test resolving website by numeric ID"""
        website = self.mixin._resolve_website(str(self.website.id))
        self.assertEqual(website.id, self.website.id)

    def test_resolve_website_by_int_id(self):
        """Test resolving website by integer ID"""
        website = self.mixin._resolve_website(self.website.id)
        self.assertEqual(website.id, self.website.id)

    def test_resolve_website_by_name(self):
        """Test resolving website by name"""
        website = self.mixin._resolve_website(self.website.name)
        self.assertEqual(website.id, self.website.id)

    def test_resolve_website_not_found(self):
        """Test resolving non-existent website"""
        with self.assertRaises(UserError):
            self.mixin._resolve_website("NonExistentWebsite999")

    def test_resolve_website_id_not_found(self):
        """Test resolving non-existent website by ID"""
        with self.assertRaises(UserError):
            self.mixin._resolve_website("999999")

    def test_resolve_page_by_url(self):
        """Test resolving page by URL"""
        # Create a page to resolve
        result = self.website.new_page(name="Mixin Resolve Test", add_menu=False)
        page = self.env["website.page"].browse(result["page_id"])
        resolved = self.mixin._resolve_page(page.url)
        self.assertEqual(resolved.id, page.id)

    def test_resolve_page_by_name(self):
        """Test resolving page by name"""
        result = self.website.new_page(name="Mixin Name Test", add_menu=False)
        page = self.env["website.page"].browse(result["page_id"])
        resolved = self.mixin._resolve_page("Mixin Name Test")
        self.assertEqual(resolved.id, page.id)

    def test_resolve_page_not_found(self):
        """Test resolving non-existent page"""
        with self.assertRaises(UserError):
            self.mixin._resolve_page("/nonexistent-page-999")

    def test_resolve_menu_not_found(self):
        """Test resolving non-existent menu"""
        with self.assertRaises(UserError):
            self.mixin._resolve_menu("NonExistentMenu999")

    def test_resolve_menu_by_id(self):
        """Test resolving menu by numeric ID"""
        menu = self.env["website.menu"].search(
            [("website_id", "=", self.website.id)], limit=1
        )
        if not menu:
            self.skipTest("No menus found")
        resolved = self.mixin._resolve_menu(str(menu.id))
        self.assertEqual(resolved.id, menu.id)

    def test_resolve_menu_by_name(self):
        """Test resolving menu by name"""
        menu = self.env["website.menu"].search(
            [("website_id", "=", self.website.id)], limit=1
        )
        if not menu:
            self.skipTest("No menus found")
        resolved = self.mixin._resolve_menu(menu.name)
        self.assertEqual(resolved.id, menu.id)

    def test_resolve_menu_id_not_found(self):
        """Test resolving non-existent menu by ID"""
        with self.assertRaises(UserError):
            self.mixin._resolve_menu("999999")
