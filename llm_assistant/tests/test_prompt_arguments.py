import json
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestPromptArguments(TransactionCase):
    """Test prompt argument auto-detection and schema synchronization"""

    def setUp(self):
        super().setUp()
        self.prompt_model = self.env["llm.prompt"]

    def test_auto_detect_arguments_on_create(self):
        """Test that arguments are auto-detected when creating a prompt"""
        prompt = self.prompt_model.create({
            "name": "Test Prompt",
            "template": "Hello {{name}}, your age is {{age}} and you live in {{city}}.",
            "format": "text"
        })
        
        # Check that arguments were auto-detected
        arguments = json.loads(prompt.arguments_json)
        self.assertIn("name", arguments)
        self.assertIn("age", arguments)
        self.assertIn("city", arguments)
        
        # Check that they are marked as required by default
        self.assertTrue(arguments["name"]["required"])
        self.assertTrue(arguments["age"]["required"])
        self.assertTrue(arguments["city"]["required"])

    def test_auto_detect_arguments_on_template_update(self):
        """Test that arguments are auto-detected when template is updated"""
        prompt = self.prompt_model.create({
            "name": "Test Prompt",
            "template": "Hello {{name}}.",
            "format": "text"
        })
        
        # Initially only has 'name' argument
        arguments = json.loads(prompt.arguments_json)
        self.assertEqual(len(arguments), 1)
        self.assertIn("name", arguments)
        
        # Update template to include more arguments
        prompt.write({
            "template": "Hello {{name}}, your email is {{email}} and phone is {{phone}}."
        })
        
        # Check that new arguments were auto-detected
        arguments = json.loads(prompt.arguments_json)
        self.assertEqual(len(arguments), 3)
        self.assertIn("name", arguments)
        self.assertIn("email", arguments)
        self.assertIn("phone", arguments)

    def test_ensure_arguments_sync(self):
        """Test the _ensure_arguments_sync method"""
        prompt = self.prompt_model.create({
            "name": "Test Prompt",
            "template": "Hello {{name}}.",
            "format": "text",
            "arguments_json": json.dumps({
                "name": {
                    "type": "string",
                    "description": "User's name",
                    "required": True
                }
            })
        })
        
        # Update template to include new argument without updating schema
        prompt.template = "Hello {{name}}, welcome to {{platform}}."
        
        # Call _ensure_arguments_sync directly
        prompt._ensure_arguments_sync()
        
        # Check that new argument was added
        arguments = json.loads(prompt.arguments_json)
        self.assertIn("platform", arguments)
        self.assertEqual(arguments["platform"]["type"], "string")
        self.assertTrue(arguments["platform"]["required"])

    def test_input_schema_json_computation(self):
        """Test that input_schema_json is computed correctly"""
        prompt = self.prompt_model.create({
            "name": "Test Prompt",
            "template": "Hello {{name}} and {{email}}.",
            "format": "text"
        })
        
        # Check that input_schema_json was computed
        self.assertIsInstance(prompt.input_schema_json, dict)
        self.assertEqual(prompt.input_schema_json["type"], "object")
        self.assertIn("properties", prompt.input_schema_json)
        self.assertIn("required", prompt.input_schema_json)
        
        # Check that properties match auto-detected arguments
        properties = prompt.input_schema_json["properties"]
        self.assertIn("name", properties)
        self.assertIn("email", properties)
        
        # Check that required fields are correctly set
        required = prompt.input_schema_json["required"]
        self.assertIn("name", required)
        self.assertIn("email", required)

    def test_undefined_arguments_detection(self):
        """Test that undefined arguments are detected correctly"""
        prompt = self.prompt_model.create({
            "name": "Test Prompt",
            "template": "Hello {{name}}, your age is {{age}}.",
            "format": "text",
            "arguments_json": json.dumps({
                "name": {
                    "type": "string",
                    "description": "User's name",
                    "required": True
                }
                # Note: 'age' is missing from schema but used in template
            })
        })
        
        # Check that undefined arguments are detected
        self.assertEqual(prompt.undefined_arguments, "age")

    def test_argument_count_computation(self):
        """Test that argument count is computed correctly"""
        prompt = self.prompt_model.create({
            "name": "Test Prompt",
            "template": "Hello {{name}}, {{greeting}} and {{farewell}}.",
            "format": "text"
        })
        
        # Should have 3 arguments
        self.assertEqual(prompt.argument_count, 3)

    def test_extract_arguments_from_template(self):
        """Test the argument extraction method"""
        # Test simple variable extraction
        args = self.prompt_model._extract_arguments_from_template(
            "Hello {{name}}, your age is {{age}}."
        )
        self.assertEqual(args, {"name", "age"})
        
        # Test with spaces
        args = self.prompt_model._extract_arguments_from_template(
            "Hello {{ name }}, your age is {{ age }}."
        )
        self.assertEqual(args, {"name", "age"})
        
        # Test with no arguments
        args = self.prompt_model._extract_arguments_from_template(
            "Hello world, no variables here."
        )
        self.assertEqual(args, set())
        
        # Test with duplicate arguments
        args = self.prompt_model._extract_arguments_from_template(
            "Hello {{name}}, again {{name}}."
        )
        self.assertEqual(args, {"name"})
