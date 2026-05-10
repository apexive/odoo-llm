"""Tests for website page management tools"""

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestPageTools(TransactionCase):
    """Test page find, create, update, publish, clone, delete tools"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.page_tools = cls.env["website.tool.page"]
        cls.website = cls.env["website"].search([], limit=1)
        if not cls.website:
            raise Exception("No website found for testing")

        # Create a test page
        result = cls.website.new_page(name="LLM Test Page", add_menu=False)
        cls.test_page = cls.env["website.page"].browse(result["page_id"])

    def test_find_pages(self):
        """Test finding pages by name"""
        result = self.page_tools.website_find_pages(name="LLM Test")
        self.assertGreaterEqual(result["count"], 1)
        names = [p["name"] for p in result["pages"]]
        self.assertTrue(any("LLM Test" in n for n in names))

    def test_find_pages_by_url(self):
        """Test finding pages by URL"""
        result = self.page_tools.website_find_pages(url=self.test_page.url)
        self.assertGreaterEqual(result["count"], 1)

    def test_find_pages_by_publish_status(self):
        """Test finding pages by publish status"""
        result = self.page_tools.website_find_pages(is_published=False)
        self.assertIsInstance(result["pages"], list)

    def test_find_pages_returns_correct_fields(self):
        """Test that find results have all expected fields"""
        result = self.page_tools.website_find_pages(name="LLM Test Page")
        self.assertGreater(result["count"], 0)
        page = result["pages"][0]
        for field in [
            "id",
            "name",
            "url",
            "is_published",
            "website_indexed",
        ]:
            self.assertIn(field, page)

    def test_create_page(self):
        """Test creating a new page"""
        result = self.page_tools.website_create_page(name="New LLM Page")
        self.assertIn("id", result)
        self.assertIn("url", result)
        self.assertTrue(result["url"])
        self.assertIn("message", result)

    def test_create_page_with_menu(self):
        """Test creating a page with a menu item"""
        result = self.page_tools.website_create_page(
            name="Page With Menu LLM", add_menu=True
        )
        self.assertIn("menu_id", result)

    def test_update_page(self):
        """Test updating page properties"""
        result = self.page_tools.website_update_page(
            page=self.test_page.url,
            website_indexed=False,
        )
        self.assertEqual(result["id"], self.test_page.id)
        self.test_page.invalidate_recordset()
        self.assertFalse(self.test_page.website_indexed)

        # Restore
        self.test_page.website_indexed = True

    def test_update_page_header_footer(self):
        """Test updating header/footer visibility"""
        self.page_tools.website_update_page(
            page=self.test_page.url,
            header_visible=False,
            footer_visible=False,
        )
        self.test_page.invalidate_recordset()
        self.assertFalse(self.test_page.header_visible)
        self.assertFalse(self.test_page.footer_visible)

        # Restore
        self.test_page.write({"header_visible": True, "footer_visible": True})

    def test_update_page_no_fields_raises(self):
        """Test that updating with no fields raises error"""
        with self.assertRaises(UserError):
            self.page_tools.website_update_page(page=self.test_page.url)

    def test_publish_unpublish_page(self):
        """Test publishing and unpublishing a page"""
        result = self.page_tools.website_publish_page(
            page=self.test_page.url, publish=True
        )
        self.assertTrue(result["is_published"])

        result = self.page_tools.website_publish_page(
            page=self.test_page.url, publish=False
        )
        self.assertFalse(result["is_published"])

    def test_clone_page(self):
        """Test cloning a page"""
        result = self.page_tools.website_clone_page(
            page=self.test_page.url,
            new_name="Cloned LLM Page",
        )
        self.assertIn("url", result)
        self.assertTrue(result["url"])
        self.assertIn("message", result)

    def test_delete_page(self):
        """Test deleting a page"""
        create_result = self.page_tools.website_create_page(name="Page To Delete LLM")
        page = self.env["website.page"].browse(create_result["id"])
        self.assertTrue(page.exists())

        result = self.page_tools.website_delete_page(page=page.url)
        self.assertIn("message", result)
        self.assertFalse(page.exists())

    def test_find_page_not_found_raises(self):
        """Test that finding non-existent page raises error in update"""
        with self.assertRaises(UserError):
            self.page_tools.website_update_page(
                page="/nonexistent-page-999",
                name="New Name",
            )
