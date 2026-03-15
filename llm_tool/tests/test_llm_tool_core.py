from unittest.mock import patch

from psycopg2 import IntegrityError

from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import LLMToolCase


@tagged("post_install", "-at_install")
class TestLLMToolCore(LLMToolCase):
    """Test core llm.tool model functionality"""

    def test_create_tool(self):
        """Test basic tool creation"""
        tool = self._create_test_tool(name="my_tool", description="My test tool")

        self.assertEqual(tool.name, "my_tool")
        self.assertEqual(tool.description, "My test tool")
        self.assertEqual(tool.implementation, "function")
        self.assertTrue(tool.active)

    def test_get_decorated_method_missing_model_field(self):
        """Test _get_decorated_method() raises ValueError for missing model"""
        tool = self._create_test_tool(decorator_model="", decorator_method="method")

        with self.assertRaises(ValueError) as ctx:
            tool._get_decorated_method()

        self.assertIn("missing decorator_model", str(ctx.exception))

    def test_get_decorated_method_missing_method_field(self):
        """Test _get_decorated_method() raises ValueError for missing method"""
        tool = self._create_test_tool(decorator_model="res.users", decorator_method="")

        with self.assertRaises(ValueError) as ctx:
            tool._get_decorated_method()

        self.assertIn("missing", str(ctx.exception).lower())

    def test_get_decorated_method_nonexistent_model(self):
        """Test _get_decorated_method() raises KeyError for non-existent model"""
        tool = self._create_test_tool(
            decorator_model="nonexistent.model", decorator_method="some_method"
        )

        with self.assertRaises(KeyError):
            tool._get_decorated_method()

    def test_get_decorated_method_nonexistent_method(self):
        """Test _get_decorated_method() raises AttributeError for non-existent method"""
        tool = self._create_test_tool(
            decorator_model="res.users", decorator_method="nonexistent_method_xyz"
        )

        with self.assertRaises(AttributeError) as ctx:
            tool._get_decorated_method()

        self.assertIn("not found", str(ctx.exception).lower())

    def test_get_decorated_method_success(self):
        """Test _get_decorated_method() retrieves existing method"""
        # Use a method that exists on all models (read exists on all Odoo models)
        tool = self._create_test_tool(
            decorator_model="res.users", decorator_method="read"
        )

        method = tool._get_decorated_method()

        self.assertTrue(callable(method))
        self.assertEqual(method.__name__, "read")

    def test_execute_unimplemented_implementation_raises_error(self):
        """Test execute() raises NotImplementedError for missing {implementation}_execute method"""

        # Patch _get_available_implementations to allow a dummy implementation
        def patched_implementations():
            return [
                ("function", "Function"),
                ("dummy_implementation", "Dummy"),
            ]

        with patch.object(
            type(self.LLMTool),
            "_get_available_implementations",
            patched_implementations,
        ):
            # Create tool with dummy implementation
            tool = self.LLMTool.create(
                {
                    "name": "test_dummy_tool",
                    "description": "Test tool with unimplemented implementation",
                    "implementation": "dummy_implementation",
                }
            )

            # Attempting to execute should raise NotImplementedError
            with self.assertRaises(NotImplementedError) as ctx:
                tool.execute({})

            self.assertIn("dummy_implementation_execute", str(ctx.exception))

    def test_get_tool_definition_uses_description_from_db(self):
        """Test get_tool_definition() uses description from DB field"""
        tool = self._create_test_tool(
            name="test_tool",
            description="Custom description from DB",
            decorator_model="res.users",
            decorator_method="read",
        )

        definition = tool.get_tool_definition()

        self.assertEqual(definition["description"], "Custom description from DB")

    def test_tool_active_field(self):
        """Test tool active field behavior"""
        tool = self._create_test_tool()

        # Default should be active
        self.assertTrue(tool.active)

        # Can be deactivated
        tool.active = False
        self.assertFalse(tool.active)

    def test_tool_annotations_in_definition(self):
        """Test tool annotations are included in get_tool_definition()"""
        tool = self._create_test_tool(
            decorator_model="res.users",
            decorator_method="read",
            read_only_hint=True,
            idempotent_hint=True,
            destructive_hint=False,
        )

        definition = tool.get_tool_definition()

        # Should have annotations
        self.assertIn("annotations", definition)
        annotations = definition["annotations"]
        self.assertTrue(annotations["readOnlyHint"])
        self.assertTrue(annotations["idempotentHint"])
        self.assertFalse(annotations["destructiveHint"])

    def test_tool_title_in_definition(self):
        """Test tool title is included in get_tool_definition()"""
        tool = self._create_test_tool(
            name="test_tool",
            title="Custom Tool Title",
            decorator_model="res.users",
            decorator_method="read",
        )

        definition = tool.get_tool_definition()

        self.assertEqual(definition["title"], "Custom Tool Title")

    def test_tool_title_defaults_to_name(self):
        """Test tool title defaults to name when not set"""
        tool = self._create_test_tool(
            name="test_tool",
            title=False,
            decorator_model="res.users",
            decorator_method="read",
        )

        definition = tool.get_tool_definition()

        self.assertEqual(definition["title"], "test_tool")

    @mute_logger("odoo.sql_db")
    def test_duplicate_tool_name_constraint(self):
        """Test that duplicate tool names are prevented by SQL constraint"""
        self._create_test_tool(name="duplicate_tool", description="First tool")

        # Attempt to create another tool with same name
        with self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self._create_test_tool(name="duplicate_tool", description="Second tool")

    @mute_logger("odoo.sql_db")
    def test_duplicate_function_tool_constraint(self):
        """Test that duplicate function tools are prevented by SQL constraint"""
        self._create_test_tool(
            name="first_tool",
            decorator_model="res.users",
            decorator_method="read",
        )

        # Attempt to create another tool with same model+method
        with self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self._create_test_tool(
                    name="second_tool",
                    decorator_model="res.users",
                    decorator_method="read",
                )

    def test_different_function_tools_allowed(self):
        """Test that different function tools can coexist"""
        tool1 = self._create_test_tool(
            name="tool_one",
            decorator_model="res.users",
            decorator_method="read",
        )
        tool2 = self._create_test_tool(
            name="tool_two",
            decorator_model="res.users",
            decorator_method="write",  # Different method
        )

        self.assertTrue(tool1.exists())
        self.assertTrue(tool2.exists())
        self.assertNotEqual(tool1.id, tool2.id)
