"""Tests for website page content tools"""

from odoo.tests.common import TransactionCase


class TestContentTools(TransactionCase):
    """Test page content read and write tools"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.content_tools = cls.env["website.tool.content"]
        cls.website = cls.env["website"].search([], limit=1)
        if not cls.website:
            raise Exception("No website found for testing")

        # Create a test page
        result = cls.website.new_page(name="LLM Content Test Page", add_menu=False)
        cls.test_page = cls.env["website.page"].browse(result["page_id"])

    def test_get_page_content(self):
        """Test reading page content"""
        result = self.content_tools.website_get_page_content(
            page=self.test_page.url,
        )
        self.assertEqual(result["page_id"], self.test_page.id)
        self.assertEqual(result["view_id"], self.test_page.view_id.id)
        self.assertEqual(result["name"], self.test_page.name)
        self.assertEqual(result["url"], self.test_page.url)
        self.assertIn("content", result)
        self.assertTrue(result["content"])

    def test_get_page_content_by_name(self):
        """Test reading page content by name"""
        result = self.content_tools.website_get_page_content(
            page="LLM Content Test Page",
        )
        self.assertEqual(result["page_id"], self.test_page.id)

    def test_update_page_content(self):
        """Test writing page content"""
        new_content = (
            '<t t-name="website.llm_content_test_page">'
            '<t t-call="website.layout">'
            "<div>Updated by LLM test</div>"
            "</t></t>"
        )
        result = self.content_tools.website_update_page_content(
            page=self.test_page.url,
            content=new_content,
        )
        self.assertEqual(result["page_id"], self.test_page.id)
        self.assertIn("message", result)

        # Verify content was updated
        self.test_page.view_id.invalidate_recordset()
        self.assertIn("Updated by LLM test", self.test_page.view_id.arch)

    def test_get_content_returns_fields(self):
        """Test that get_content returns all expected fields"""
        result = self.content_tools.website_get_page_content(
            page=self.test_page.url,
        )
        for field in ["page_id", "view_id", "name", "url", "content"]:
            self.assertIn(field, result)

    def test_update_content_returns_fields(self):
        """Test that update_content returns all expected fields"""
        result = self.content_tools.website_update_page_content(
            page=self.test_page.url,
            content=self.test_page.view_id.arch,
        )
        for field in ["page_id", "view_id", "name", "url", "message"]:
            self.assertIn(field, result)
