import json
from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestThreadSchema(TransactionCase):
    """Test thread schema handling and form configuration"""

    def setUp(self):
        super().setUp()
        self.thread_model = self.env["llm.thread"]
        self.prompt_model = self.env["llm.prompt"]
        self.provider_model = self.env["llm.provider"]
        self.model_model = self.env["llm.model"]

        # Create a test provider
        self.test_provider = self.provider_model.create(
            {
                "name": "Test Provider",
                "service": "test",
            }
        )

        # Create a test model with input schema already populated
        # Use "text" model_use to avoid triggering auto-generation
        # (schema generation is tested in provider-specific modules)
        self.test_model = self.model_model.create(
            {
                "name": "test-model",
                "provider_id": self.test_provider.id,
                "model_use": "text",
                "details": {
                    "input_schema": {
                        "type": "object",
                        "properties": {"model_field": {"type": "string"}},
                    }
                },
            }
        )

        # Create a test prompt with schema
        # Note: input_schema_json is computed from arguments_json
        self.test_prompt = self.prompt_model.create(
            {
                "name": "Test Schema Prompt",
                "template": "Hello {{name}}, you are {{age}} years old.",
                "format": "text",
                "arguments_json": json.dumps(
                    {
                        "name": {
                            "type": "string",
                            "default": "John",
                            "description": "Person's name",
                        },
                        "age": {
                            "type": "integer",
                            "default": 30,
                            "description": "Person's age",
                        },
                    }
                ),
            }
        )

    def test_get_input_schema_from_model(self):
        """Test that schema is retrieved from model when no prompt"""
        thread = self.thread_model.new({"name": "Test Thread"})
        thread.model_id = self.test_model

        schema = thread.get_input_schema()
        self.assertIn("model_field", schema.get("properties", {}))
        self.assertEqual(schema["properties"]["model_field"]["type"], "string")

    def test_get_input_schema_from_prompt(self):
        """Test that schema is retrieved from prompt when available"""
        # Create a real thread record with all required fields
        thread = self.thread_model.create(
            {
                "name": "Test Thread",
                "provider_id": self.test_provider.id,
                "model_id": self.test_model.id,
                "prompt_id": self.test_prompt.id,
            }
        )

        schema = thread.get_input_schema()

        # Should have prompt schema properties
        self.assertIn("name", schema.get("properties", {}))
        self.assertIn("age", schema.get("properties", {}))

    def test_get_form_defaults_with_schema(self):
        """Test that form defaults include context values"""
        thread = self.thread_model.new({"name": "Test Thread"})

        # Mock get_context at the class level instead of instance level
        with patch.object(type(thread), "get_context", return_value={"name": "John"}):
            defaults = thread.get_form_defaults()

            # Should include context value
            self.assertEqual(defaults.get("name"), "John")

    def test_ensure_dict_conversion(self):
        """Test the _ensure_dict helper method"""
        thread = self.thread_model.new()

        # Test with dict input
        result = thread._ensure_dict({"key": "value"})
        self.assertEqual(result, {"key": "value"})

        # Test with JSON string input
        result = thread._ensure_dict('{"key": "value"}')
        self.assertEqual(result, {"key": "value"})

        # Test with invalid JSON string
        result = thread._ensure_dict("invalid json")
        self.assertEqual(result, {})

        # Test with None/other types
        result = thread._ensure_dict(None)
        self.assertEqual(result, {})

    def test_prepare_generation_inputs_with_prompt(self):
        """Test input preparation with prompt template rendering"""
        thread = self.thread_model.new({"name": "Test Thread"})
        thread.prompt_id = self.test_prompt

        # Mock get_context at class level
        with patch.object(type(thread), "get_context", return_value={"name": "Alice"}):
            # Test with additional inputs
            inputs = {"age": 25}

            # Mock the template rendering at the location where it's imported
            with patch(
                "odoo.addons.llm_generate.models.llm_thread.render_template"
            ) as mock_render:
                mock_render.return_value = '{"messages": [{"role": "user", "content": "Hello Alice, you are 25 years old."}]}'

                result = thread.prepare_generation_inputs(inputs)

                # Should have called render_template with merged inputs
                mock_render.assert_called_once()
                # render_template is called with (template, context) as positional args
                call_args = mock_render.call_args[0]  # Get positional arguments
                self.assertEqual(call_args[1]["name"], "Alice")
                self.assertEqual(call_args[1]["age"], 25)

                # Should return parsed JSON
                self.assertIsInstance(result, dict)
                self.assertIn("messages", result)

    def test_prepare_generation_inputs_without_prompt(self):
        """Test input preparation without prompt (direct passthrough)"""
        thread = self.thread_model.new({"name": "Test Thread"})
        # No prompt_id set

        # Mock get_context at class level
        with patch.object(
            type(thread), "get_context", return_value={"context_var": "value"}
        ):
            inputs = {"user_input": "test"}

            result = thread.prepare_generation_inputs(inputs)

            # Should return merged context + inputs
            self.assertEqual(result["context_var"], "value")
            self.assertEqual(result["user_input"], "test")

    def test_prepare_generation_inputs_error_handling(self):
        """Test error handling in input preparation"""
        thread = self.thread_model.new({"name": "Test Thread"})
        thread.prompt_id = self.test_prompt

        # Mock get_context at class level
        with patch.object(type(thread), "get_context", return_value={"name": "Bob"}):
            inputs = {"age": 30}

            # Mock template rendering to raise an exception
            with patch(
                "odoo.addons.llm_generate.models.llm_thread.render_template"
            ) as mock_render:
                mock_render.side_effect = Exception("Template error")

                result = thread.prepare_generation_inputs(inputs)

                # Should fall back to merged inputs on error
                self.assertEqual(result["name"], "Bob")
                self.assertEqual(result["age"], 30)
