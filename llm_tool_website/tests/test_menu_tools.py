"""Tests for website menu management tools"""

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestMenuTools(TransactionCase):
    """Test menu tree, find, create, update, delete tools"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.menu_tools = cls.env["website.tool.menu"]
        cls.website = cls.env["website"].search([], limit=1)

    def test_get_menu_tree(self):
        """Test getting the full menu tree"""
        result = self.menu_tools.website_get_menu_tree()
        self.assertIn("menu_tree", result)
        tree = result["menu_tree"]
        self.assertIn("children", tree)
        self.assertIn("name", tree)
        self.assertIn("id", tree)

    def test_find_menus(self):
        """Test finding menus"""
        result = self.menu_tools.website_find_menus()
        self.assertIn("menus", result)
        self.assertGreater(result["count"], 0)

    def test_find_menus_by_name(self):
        """Test finding menus by name"""
        menu = self.env["website.menu"].search(
            [("website_id", "=", self.website.id)], limit=1
        )
        if not menu:
            self.skipTest("No menus found")
        result = self.menu_tools.website_find_menus(name=menu.name)
        self.assertGreater(result["count"], 0)

    def test_find_menus_result_fields(self):
        """Test that find results have all expected fields"""
        result = self.menu_tools.website_find_menus()
        if result["count"] == 0:
            self.skipTest("No menus found")
        menu = result["menus"][0]
        for field in ["id", "name", "url", "sequence", "parent"]:
            self.assertIn(field, menu)

    def test_create_menu(self):
        """Test creating a menu item"""
        result = self.menu_tools.website_create_menu(
            name="LLM Test Menu",
            url="/llm-test-menu",
        )
        self.assertIn("id", result)
        self.assertEqual(result["name"], "LLM Test Menu")
        self.assertEqual(result["url"], "/llm-test-menu")

    def test_create_submenu(self):
        """Test creating a submenu item"""
        parent_result = self.menu_tools.website_create_menu(
            name="LLM Parent Menu",
            url="/llm-parent",
        )
        result = self.menu_tools.website_create_menu(
            name="LLM Child Menu",
            url="/llm-child",
            parent=str(parent_result["id"]),
        )
        self.assertEqual(result["parent"], "LLM Parent Menu")

    def test_create_menu_new_window(self):
        """Test creating a menu with new_window=True"""
        result = self.menu_tools.website_create_menu(
            name="External Link Menu",
            url="https://example.com",
            new_window=True,
        )
        menu = self.env["website.menu"].browse(result["id"])
        self.assertTrue(menu.new_window)

    def test_update_menu(self):
        """Test updating a menu item"""
        create_result = self.menu_tools.website_create_menu(
            name="Menu To Update",
            url="/menu-update",
        )
        result = self.menu_tools.website_update_menu(
            menu=str(create_result["id"]),
            name="Updated Menu Name",
            url="/updated-url",
        )
        self.assertEqual(result["name"], "Updated Menu Name")
        self.assertEqual(result["url"], "/updated-url")

    def test_update_menu_sequence(self):
        """Test updating menu sequence"""
        create_result = self.menu_tools.website_create_menu(
            name="Sequence Menu",
            url="/seq-menu",
        )
        self.menu_tools.website_update_menu(
            menu=str(create_result["id"]),
            sequence=99,
        )
        menu = self.env["website.menu"].browse(create_result["id"])
        self.assertEqual(menu.sequence, 99)

    def test_update_menu_no_fields_raises(self):
        """Test that updating with no fields raises error"""
        menu = self.env["website.menu"].search(
            [("website_id", "=", self.website.id)], limit=1
        )
        if not menu:
            self.skipTest("No menus found")
        with self.assertRaises(UserError):
            self.menu_tools.website_update_menu(menu=str(menu.id))

    def test_delete_menu(self):
        """Test deleting a menu item"""
        create_result = self.menu_tools.website_create_menu(
            name="Menu To Delete",
            url="/menu-delete",
        )
        result = self.menu_tools.website_delete_menu(menu=str(create_result["id"]))
        self.assertIn("message", result)
        menu = self.env["website.menu"].browse(create_result["id"])
        self.assertFalse(menu.exists())

    def test_delete_menu_with_children(self):
        """Test deleting a menu with children reports count"""
        parent_result = self.menu_tools.website_create_menu(
            name="Parent To Delete",
            url="/parent-delete",
        )
        self.menu_tools.website_create_menu(
            name="Child To Delete",
            url="/child-delete",
            parent=str(parent_result["id"]),
        )
        result = self.menu_tools.website_delete_menu(menu=str(parent_result["id"]))
        self.assertEqual(result["children_deleted"], 1)
