"""Tests for website redirect management tools"""

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestRedirectTools(TransactionCase):
    """Test redirect find, create, update, delete tools"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.redirect_tools = cls.env["website.tool.redirect"]
        cls.website = cls.env["website"].search([], limit=1)

    def test_find_redirects(self):
        """Test finding redirects"""
        result = self.redirect_tools.website_find_redirects()
        self.assertIn("redirects", result)
        self.assertIsInstance(result["redirects"], list)

    def test_create_redirect_permanent(self):
        """Test creating a permanent redirect"""
        result = self.redirect_tools.website_create_redirect(
            name="Test Permanent Redirect",
            url_from="/old-page-llm",
            url_to="/new-page-llm",
            redirect_type="permanent",
        )
        self.assertIn("id", result)
        self.assertEqual(result["redirect_code"], "301")
        self.assertEqual(result["redirect_type"], "permanent")

    def test_create_redirect_temporary(self):
        """Test creating a temporary redirect"""
        result = self.redirect_tools.website_create_redirect(
            name="Test Temp Redirect",
            url_from="/temp-old-llm",
            url_to="/temp-new-llm",
            redirect_type="temporary",
        )
        self.assertEqual(result["redirect_code"], "302")

    def test_create_redirect_default_type(self):
        """Test that default redirect type is permanent"""
        result = self.redirect_tools.website_create_redirect(
            name="Default Type Redirect",
            url_from="/default-old-llm",
            url_to="/default-new-llm",
        )
        self.assertEqual(result["redirect_code"], "301")

    def test_create_redirect_invalid_type(self):
        """Test creating redirect with invalid type raises error"""
        with self.assertRaises(UserError):
            self.redirect_tools.website_create_redirect(
                name="Bad Redirect",
                url_from="/bad-llm",
                url_to="/bad2-llm",
                redirect_type="invalid_type",
            )

    def test_find_redirects_by_url_from(self):
        """Test finding redirects by source URL"""
        self.redirect_tools.website_create_redirect(
            name="Findable Redirect",
            url_from="/findable-old-llm",
            url_to="/findable-new-llm",
        )
        result = self.redirect_tools.website_find_redirects(
            url_from="/findable-old-llm"
        )
        self.assertGreater(result["count"], 0)

    def test_find_redirects_by_type(self):
        """Test finding redirects by type"""
        self.redirect_tools.website_create_redirect(
            name="Typed Redirect",
            url_from="/typed-old-llm",
            url_to="/typed-new-llm",
            redirect_type="temporary",
        )
        result = self.redirect_tools.website_find_redirects(redirect_type="temporary")
        self.assertGreater(result["count"], 0)
        for redir in result["redirects"]:
            self.assertEqual(redir["redirect_code"], "302")

    def test_find_redirects_result_fields(self):
        """Test that results have all expected fields"""
        self.redirect_tools.website_create_redirect(
            name="Fields Redirect",
            url_from="/fields-old-llm",
            url_to="/fields-new-llm",
        )
        result = self.redirect_tools.website_find_redirects(url_from="/fields-old-llm")
        redir = result["redirects"][0]
        for field in [
            "id",
            "name",
            "url_from",
            "url_to",
            "redirect_type",
            "redirect_code",
            "active",
        ]:
            self.assertIn(field, redir)

    def test_update_redirect(self):
        """Test updating a redirect rule"""
        create_result = self.redirect_tools.website_create_redirect(
            name="Update Redirect",
            url_from="/update-old-llm",
            url_to="/update-new-llm",
        )
        result = self.redirect_tools.website_update_redirect(
            redirect_id=create_result["id"],
            name="Updated Redirect Name",
            redirect_type="temporary",
        )
        self.assertEqual(result["name"], "Updated Redirect Name")
        self.assertEqual(result["redirect_code"], "302")

    def test_update_redirect_active(self):
        """Test disabling a redirect"""
        create_result = self.redirect_tools.website_create_redirect(
            name="Active Redirect",
            url_from="/active-old-llm",
            url_to="/active-new-llm",
        )
        result = self.redirect_tools.website_update_redirect(
            redirect_id=create_result["id"],
            active=False,
        )
        self.assertFalse(result["active"])

    def test_update_redirect_not_found(self):
        """Test updating non-existent redirect raises error"""
        with self.assertRaises(UserError):
            self.redirect_tools.website_update_redirect(redirect_id=999999)

    def test_update_redirect_no_fields_raises(self):
        """Test updating with no fields raises error"""
        create_result = self.redirect_tools.website_create_redirect(
            name="No Fields Redirect",
            url_from="/no-fields-old-llm",
            url_to="/no-fields-new-llm",
        )
        with self.assertRaises(UserError):
            self.redirect_tools.website_update_redirect(redirect_id=create_result["id"])

    def test_update_redirect_invalid_type(self):
        """Test updating with invalid redirect type raises error"""
        create_result = self.redirect_tools.website_create_redirect(
            name="Invalid Type Redirect",
            url_from="/invalid-type-old-llm",
            url_to="/invalid-type-new-llm",
        )
        with self.assertRaises(UserError):
            self.redirect_tools.website_update_redirect(
                redirect_id=create_result["id"],
                redirect_type="invalid",
            )

    def test_delete_redirect(self):
        """Test deleting a redirect rule"""
        create_result = self.redirect_tools.website_create_redirect(
            name="Delete Redirect",
            url_from="/delete-old-llm",
            url_to="/delete-new-llm",
        )
        result = self.redirect_tools.website_delete_redirect(
            redirect_id=create_result["id"]
        )
        self.assertIn("message", result)
        redir = self.env["website.rewrite"].browse(create_result["id"])
        self.assertFalse(redir.exists())

    def test_delete_redirect_not_found(self):
        """Test deleting non-existent redirect raises error"""
        with self.assertRaises(UserError):
            self.redirect_tools.website_delete_redirect(redirect_id=999999)
