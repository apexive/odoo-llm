"""Tests for website visitor analytics tools"""

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestVisitorTools(TransactionCase):
    """Test visitor stats, find, and detail tools"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.visitor_tools = cls.env["website.tool.visitor"]
        cls.website = cls.env["website"].search([], limit=1)

    def test_visitor_stats(self):
        """Test getting visitor statistics"""
        result = self.visitor_tools.website_visitor_stats()
        self.assertIn("total_visitors", result)
        self.assertIn("connected_visitors", result)
        self.assertIn("identified_visitors", result)
        self.assertIn("top_pages", result)
        self.assertIsInstance(result["top_pages"], list)

    def test_visitor_stats_with_dates(self):
        """Test getting visitor statistics with date filter"""
        result = self.visitor_tools.website_visitor_stats(
            date_from="2020-01-01",
            date_to="2099-12-31",
        )
        self.assertIn("total_visitors", result)

    def test_find_visitors(self):
        """Test finding visitors"""
        result = self.visitor_tools.website_find_visitors()
        self.assertIn("visitors", result)
        self.assertIsInstance(result["visitors"], list)

    def test_find_visitors_by_country(self):
        """Test finding visitors filtered by country"""
        result = self.visitor_tools.website_find_visitors(country="US")
        self.assertIn("visitors", result)
        self.assertIsInstance(result["visitors"], list)

    def test_find_visitors_result_fields(self):
        """Test that visitor results have expected fields"""
        result = self.visitor_tools.website_find_visitors()
        if result["count"] == 0:
            self.skipTest("No visitors found")
        visitor = result["visitors"][0]
        for field in [
            "id",
            "name",
            "visit_count",
            "is_connected",
        ]:
            self.assertIn(field, visitor)

    def test_visitor_detail_not_found(self):
        """Test getting detail for non-existent visitor"""
        with self.assertRaises(UserError):
            self.visitor_tools.website_visitor_detail(visitor_id=999999)

    def test_find_visitors_connected_filter(self):
        """Test finding visitors by connection status"""
        result = self.visitor_tools.website_find_visitors(is_connected=False)
        self.assertIn("visitors", result)
        for visitor in result["visitors"]:
            self.assertFalse(visitor["is_connected"])
