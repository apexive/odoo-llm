"""Integration tests for @llm_tool decorator and auto-registration"""

from pydantic import ValidationError

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDecoratorRegistration(TransactionCase):
    """Test @llm_tool decorator registration and lifecycle"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.LLMTool = cls.env["llm.tool"]

    def test_demo_tools_auto_registered(self):
        """Test that demo tools are automatically registered"""
        # Tools from llm_tool_demo should be registered
        expected_tools = [
            ("res.users", "get_system_info"),
            ("res.users", "send_notification_to_user"),
            ("llm.utility.tools", "calculate_business_days"),
            ("crm.lead", "create_lead_from_description"),
            ("sale.order", "generate_sales_report"),
            ("ir.model", "get_record_info"),
        ]

        for model, method in expected_tools:
            tool = self.LLMTool.search(
                [
                    ("implementation", "=", "function"),
                    ("decorator_model", "=", model),
                    ("decorator_method", "=", method),
                ],
                limit=1,
            )
            self.assertTrue(
                tool.exists(),
                f"Tool {model}.{method} should be auto-registered",
            )
            self.assertTrue(tool.active, f"Tool {model}.{method} should be active")

    def test_tool_has_correct_metadata(self):
        """Test that registered tools have correct metadata from decorator"""
        # Check get_system_info tool
        tool = self.LLMTool.search(
            [
                ("decorator_model", "=", "res.users"),
                ("decorator_method", "=", "get_system_info"),
            ],
            limit=1,
        )

        self.assertTrue(tool.exists())
        self.assertEqual(tool.name, "get_system_info")
        self.assertEqual(tool.implementation, "function")
        # Should have description from docstring
        self.assertTrue(len(tool.description) > 0)
        # Should have correct hints
        self.assertTrue(tool.read_only_hint)
        self.assertTrue(tool.idempotent_hint)

    def test_tool_with_manual_schema_stored(self):
        """Test that tools with manual schema have it stored in DB"""
        # get_record_info has manual schema
        tool = self.LLMTool.search(
            [
                ("decorator_model", "=", "ir.model"),
                ("decorator_method", "=", "get_record_info"),
            ],
            limit=1,
        )

        self.assertTrue(tool.exists())
        self.assertTrue(tool.input_schema, "Manual schema should be stored")

        # Verify schema content
        import json

        schema = json.loads(tool.input_schema)
        self.assertEqual(schema["type"], "object")
        self.assertIn("model_name", schema["properties"])
        self.assertIn("record_id", schema["properties"])

    def test_tool_execution_works(self):
        """Test that registered tools can be executed"""
        # Test calculate_business_days execution
        tool = self.LLMTool.search(
            [
                ("decorator_model", "=", "llm.utility.tools"),
                ("decorator_method", "=", "calculate_business_days"),
            ],
            limit=1,
        )

        self.assertTrue(tool.exists())

        # Execute the tool
        result = tool.execute(
            {
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "exclude_weekends": True,
            }
        )

        # Verify result structure
        self.assertIsInstance(result, dict)
        self.assertIn("business_days", result)
        self.assertIn("total_days", result)
        self.assertEqual(result["total_days"], 31)

    def test_tool_schema_generation(self):
        """Test that tools generate correct input schema"""
        # Test calculate_business_days schema
        tool = self.LLMTool.search(
            [
                ("decorator_model", "=", "llm.utility.tools"),
                ("decorator_method", "=", "calculate_business_days"),
            ],
            limit=1,
        )

        schema = tool.get_input_schema()

        # Should have properties for the typed parameters
        self.assertEqual(schema["type"], "object")
        self.assertIn("properties", schema)
        properties = schema["properties"]

        # Check parameter types
        self.assertIn("start_date", properties)
        self.assertIn("end_date", properties)
        self.assertIn("exclude_weekends", properties)

        # Check required fields
        self.assertIn("required", schema)
        self.assertIn("start_date", schema["required"])
        self.assertIn("end_date", schema["required"])
        # exclude_weekends has default, so not required
        self.assertNotIn("exclude_weekends", schema["required"])

    def test_tool_with_no_parameters(self):
        """Test that tools with no parameters work correctly"""
        # get_system_info has no parameters except self
        tool = self.LLMTool.search(
            [
                ("decorator_model", "=", "res.users"),
                ("decorator_method", "=", "get_system_info"),
            ],
            limit=1,
        )

        # Execute with empty params
        result = tool.execute({})

        # Should return system info
        self.assertIsInstance(result, dict)
        self.assertIn("database_name", result)
        self.assertIn("company_name", result)

    def test_tool_validation_errors(self):
        """Test that tool execution validates parameters"""
        tool = self.LLMTool.search(
            [
                ("decorator_model", "=", "llm.utility.tools"),
                ("decorator_method", "=", "calculate_business_days"),
            ],
            limit=1,
        )

        # Missing required parameter should raise validation error
        with self.assertRaises(ValidationError):
            tool.execute({"start_date": "2024-01-01"})  # Missing end_date

    def test_destructive_hint_metadata(self):
        """Test that destructive tools have correct hints"""
        tool = self.LLMTool.search(
            [
                ("decorator_model", "=", "crm.lead"),
                ("decorator_method", "=", "create_lead_from_description"),
            ],
            limit=1,
        )

        self.assertTrue(tool.exists())
        self.assertTrue(tool.destructive_hint)

    def test_tool_definition_complete(self):
        """Test that get_tool_definition() returns complete MCP-compatible definition"""
        tool = self.LLMTool.search(
            [
                ("decorator_model", "=", "res.users"),
                ("decorator_method", "=", "get_system_info"),
            ],
            limit=1,
        )

        definition = tool.get_tool_definition()

        # Should have all required MCP fields
        self.assertIn("name", definition)
        self.assertIn("description", definition)
        self.assertIn("inputSchema", definition)

        # Should have annotations
        self.assertIn("annotations", definition)
        annotations = definition["annotations"]
        self.assertTrue(annotations["readOnlyHint"])
        self.assertTrue(annotations["idempotentHint"])
