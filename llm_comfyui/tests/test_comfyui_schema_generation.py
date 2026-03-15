from odoo.tests.common import TransactionCase


class TestComfyUISchemaGeneration(TransactionCase):
    """Test ComfyUI-specific I/O schema generation"""

    def setUp(self):
        super().setUp()
        self.provider_model = self.env["llm.provider"]
        self.model_model = self.env["llm.model"]

        # Create test provider
        self.provider = self.provider_model.create(
            {
                "name": "Test ComfyUI Provider",
                "service": "comfyui",
            }
        )

    def test_static_schema_generation_on_create(self):
        """Test static schema generation when ComfyUI model is created"""
        model = self.model_model.create(
            {
                "name": "test-comfyui-workflow",
                "provider_id": self.provider.id,
                "model_use": "image_generation",
                "details": {},
            }
        )

        # Verify static schema was generated
        self.assertTrue(model.details.get("input_schema"))
        self.assertTrue(model.details.get("output_schema"))
        self.assertEqual(model.details["input_schema"]["type"], "object")

        # Verify ComfyUI-specific fields
        self.assertIn("prompt", model.details["input_schema"]["properties"])
        self.assertIn("client_id", model.details["input_schema"]["properties"])
        self.assertIn("number", model.details["input_schema"]["properties"])
        self.assertIn("extra_data", model.details["input_schema"]["properties"])

        # Verify required fields
        self.assertIn("prompt", model.details["input_schema"]["required"])

    def test_no_regeneration_if_schema_exists(self):
        """Test that existing custom schema is not overwritten"""
        existing_input_schema = {
            "type": "object",
            "properties": {"custom_workflow": {"type": "string"}},
        }

        model = self.model_model.create(
            {
                "name": "test-comfyui-custom",
                "provider_id": self.provider.id,
                "model_use": "image_generation",
                "details": {"input_schema": existing_input_schema},
            }
        )

        # Verify existing schema was not overwritten
        self.assertEqual(model.details["input_schema"], existing_input_schema)
        self.assertIn("custom_workflow", model.details["input_schema"]["properties"])
        # Should NOT have default ComfyUI fields
        self.assertNotIn("prompt", model.details["input_schema"]["properties"])

    def test_schema_generation_on_model_use_change(self):
        """Test schema generation when model_use changes to image_generation"""
        # Create as chat model first
        model = self.model_model.create(
            {
                "name": "test-comfyui-change",
                "provider_id": self.provider.id,
                "model_use": "chat",
                "details": {},
            }
        )

        # Verify no schema for chat model
        self.assertFalse(model.details and model.details.get("input_schema"))

        # Change to image_generation
        model.write({"model_use": "image_generation"})

        # Verify schema was generated
        self.assertTrue(model.details.get("input_schema"))
        self.assertIn("prompt", model.details["input_schema"]["properties"])

    def test_schema_for_generic_generation(self):
        """Test schema generation works for model_use='generation' too"""
        model = self.model_model.create(
            {
                "name": "test-comfyui-generic",
                "provider_id": self.provider.id,
                "model_use": "generation",  # Generic generation
                "details": {},
            }
        )

        # Verify schema was generated
        self.assertTrue(model.details.get("input_schema"))
        self.assertTrue(model.details.get("output_schema"))
        self.assertIn("prompt", model.details["input_schema"]["properties"])
