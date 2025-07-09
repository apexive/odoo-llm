import json
from unittest.mock import patch, MagicMock
from odoo.tests.common import TransactionCase


class TestThreadSchema(TransactionCase):
    """Test thread schema handling and form configuration"""

    def setUp(self):
        super().setUp()
        self.thread_model = self.env["llm.thread"]
        self.prompt_model = self.env["llm.prompt"]
        
        # Create a test prompt with schema
        self.test_prompt = self.prompt_model.create({
            "name": "Test Schema Prompt",
            "template": "Hello {{name}}, you are {{age}} years old.",
            "format": "text"
        })

    def test_get_input_schema_priority_order(self):
        """Test that schema is retrieved in the correct priority order"""
        # Mock a thread with various schema sources
        thread = self.thread_model.new({
            "name": "Test Thread"
        })
        
        # Mock the models to avoid database dependencies
        mock_model = MagicMock()
        mock_model.details = {
            "input_schema": {
                "type": "object",
                "properties": {
                    "model_field": {"type": "string"}
                }
            }
        }
        thread.model_id = mock_model
        
        # Test 1: No prompt, should return model schema
        schema = thread.get_input_schema()
        self.assertEqual(schema["properties"]["model_field"]["type"], "string")
        
        # Test 2: With prompt, should return prompt schema
        thread.prompt_id = self.test_prompt
        schema = thread.get_input_schema()
        self.assertIn("name", schema.get("properties", {}))
        self.assertIn("age", schema.get("properties", {}))

    def test_get_form_defaults_with_schema(self):
        """Test that form defaults include schema defaults"""
        thread = self.thread_model.new({
            "name": "Test Thread"
        })
        thread.prompt_id = self.test_prompt
        
        # Mock get_context to return some base values
        with patch.object(thread, 'get_context', return_value={"name": "John"}):
            defaults = thread.get_form_defaults()
            
            # Should include context value
            self.assertEqual(defaults.get("name"), "John")
            
            # Should only include properties that exist in schema
            self.assertIn("name", defaults)
            # Should not include properties not in schema
            self.assertNotIn("unknown_field", defaults)

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
        result = thread._ensure_dict('invalid json')
        self.assertEqual(result, {})
        
        # Test with None/other types
        result = thread._ensure_dict(None)
        self.assertEqual(result, {})

    def test_prepare_generation_inputs_with_prompt(self):
        """Test input preparation with prompt template rendering"""
        thread = self.thread_model.new({
            "name": "Test Thread"
        })
        thread.prompt_id = self.test_prompt
        
        # Mock get_context
        with patch.object(thread, 'get_context', return_value={"name": "Alice"}):
            # Test with additional inputs
            inputs = {"age": 25}
            
            # Mock the template rendering
            with patch('odoo.addons.llm_assistant.utils.render_template') as mock_render:
                mock_render.return_value = '{"messages": [{"role": "user", "content": "Hello Alice, you are 25 years old."}]}'
                
                result = thread.prepare_generation_inputs(inputs)
                
                # Should have called render_template with merged inputs
                mock_render.assert_called_once()
                call_args = mock_render.call_args[1]  # Get keyword arguments
                self.assertEqual(call_args["context"]["name"], "Alice")
                self.assertEqual(call_args["context"]["age"], 25)
                
                # Should return parsed JSON
                self.assertIsInstance(result, dict)
                self.assertIn("messages", result)

    def test_prepare_generation_inputs_without_prompt(self):
        """Test input preparation without prompt (direct passthrough)"""
        thread = self.thread_model.new({
            "name": "Test Thread"
        })
        # No prompt_id set
        
        # Mock get_context
        with patch.object(thread, 'get_context', return_value={"context_var": "value"}):
            inputs = {"user_input": "test"}
            
            result = thread.prepare_generation_inputs(inputs)
            
            # Should return merged context + inputs
            self.assertEqual(result["context_var"], "value")
            self.assertEqual(result["user_input"], "test")

    def test_prepare_generation_inputs_error_handling(self):
        """Test error handling in input preparation"""
        thread = self.thread_model.new({
            "name": "Test Thread"
        })
        thread.prompt_id = self.test_prompt
        
        # Mock get_context
        with patch.object(thread, 'get_context', return_value={"name": "Bob"}):
            inputs = {"age": 30}
            
            # Mock template rendering to raise an exception
            with patch('odoo.addons.llm_assistant.utils.render_template') as mock_render:
                mock_render.side_effect = Exception("Template error")
                
                result = thread.prepare_generation_inputs(inputs)
                
                # Should fall back to merged inputs on error
                self.assertEqual(result["name"], "Bob")
                self.assertEqual(result["age"], 30)
