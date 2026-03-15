import json
from unittest.mock import patch

from odoo.tests import tagged

from .common import LLMToolCase


@tagged("post_install", "-at_install")
class TestLLMToolSchema(LLMToolCase):
    """Test schema generation and storage for llm.tool"""

    def test_get_input_schema_from_stored_field(self):
        """Test get_input_schema() returns stored schema from DB field"""
        custom_schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }

        tool = self._create_test_tool(input_schema=json.dumps(custom_schema))

        result = tool.get_input_schema()

        self.assertEqual(result, custom_schema)
        self.assertIsInstance(result, dict)

    def test_get_input_schema_raises_on_invalid_json(self):
        """Test get_input_schema() raises JSONDecodeError for invalid JSON"""
        tool = self._create_test_tool(input_schema="invalid json {")

        with self.assertRaises(json.JSONDecodeError):
            tool.get_input_schema()

    def test_get_input_schema_unimplemented_implementation_raises_error(self):
        """Test get_input_schema() raises NotImplementedError for missing {implementation}_execute method"""

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
            # Create tool with dummy implementation (no stored schema)
            tool = self.LLMTool.create(
                {
                    "name": "test_dummy_schema_tool",
                    "description": "Test tool with unimplemented implementation",
                    "implementation": "dummy_implementation",
                }
            )

            # Attempting to get schema should raise NotImplementedError
            with self.assertRaises(NotImplementedError) as ctx:
                tool.get_input_schema()

            self.assertIn("dummy_implementation_execute", str(ctx.exception))

    def test_get_tool_definition_respects_stored_schema(self):
        """Test get_tool_definition() uses stored input_schema field"""
        custom_schema = {
            "type": "object",
            "properties": {"custom_field": {"type": "string"}},
        }

        tool = self._create_test_tool(
            name="test_def_tool",
            description="Test description",
            input_schema=json.dumps(custom_schema),
            decorator_model="res.users",
            decorator_method="read",  # Common method that exists on all models
        )

        definition = tool.get_tool_definition()

        # Should use the custom schema from DB
        self.assertEqual(definition["inputSchema"], custom_schema)
        self.assertEqual(definition["name"], "test_def_tool")
        self.assertEqual(definition["description"], "Test description")

    def test_action_reset_input_schema_regenerates(self):
        """Test action_reset_input_schema() regenerates schema"""
        # Create tool with custom schema
        tool = self._create_test_tool(
            decorator_model="res.users",
            decorator_method="read",
            input_schema=json.dumps({"custom": "schema"}),
        )

        original_schema = json.loads(tool.input_schema)

        # Reset should regenerate
        tool.action_reset_input_schema()

        new_schema = json.loads(tool.input_schema)

        # Schema should have changed
        self.assertNotEqual(new_schema, original_schema)
        self.assertIsInstance(new_schema, dict)

    def test_onchange_implementation_populates_empty_schema(self):
        """Test _onchange_implementation() populates schema when empty"""
        tool = self.LLMTool.new(
            {
                "name": "test_tool",
                "description": "Test",
                "decorator_model": "res.users",
                "decorator_method": "read",
            }
        )

        # Set implementation (triggers onchange)
        tool.implementation = "function"
        tool._onchange_implementation()

        # Schema should be populated
        self.assertTrue(tool.input_schema)
        schema = json.loads(tool.input_schema)
        self.assertIsInstance(schema, dict)

    def test_onchange_implementation_preserves_existing_schema(self):
        """Test _onchange_implementation() doesn't overwrite existing schema"""
        custom_schema = {"custom": "schema"}

        tool = self.LLMTool.new(
            {
                "name": "test_tool",
                "description": "Test",
                "decorator_model": "res.users",
                "decorator_method": "read",
                "input_schema": json.dumps(custom_schema),
            }
        )

        # Set implementation (triggers onchange)
        tool.implementation = "function"
        tool._onchange_implementation()

        # Schema should remain unchanged
        self.assertEqual(json.loads(tool.input_schema), custom_schema)
