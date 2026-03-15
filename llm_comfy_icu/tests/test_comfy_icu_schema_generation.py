from odoo.tests.common import TransactionCase


class TestComfyICUSchemaGeneration(TransactionCase):
    """Test ComfyICU-specific I/O schema generation"""

    def setUp(self):
        super().setUp()
        self.provider_model = self.env["llm.provider"]
        self.model_model = self.env["llm.model"]

        # Create test provider
        self.provider = self.provider_model.create(
            {
                "name": "Test ComfyICU Provider",
                "service": "comfy_icu",
            }
        )

    def test_static_schema_generation_on_create(self):
        """Test static schema generation when ComfyICU model is created"""
        model = self.model_model.create(
            {
                "name": "test-comfyicu-workflow",
                "provider_id": self.provider.id,
                "model_use": "image_generation",
                "details": {},
            }
        )

        # Verify static schema was generated
        self.assertTrue(model.details.get("input_schema"))
        self.assertTrue(model.details.get("output_schema"))
        self.assertEqual(model.details["input_schema"]["type"], "object")

        # Verify ComfyICU-specific fields
        self.assertIn("prompt", model.details["input_schema"]["properties"])
        self.assertIn("files", model.details["input_schema"]["properties"])
        self.assertIn("accelerator", model.details["input_schema"]["properties"])
        self.assertIn("webhook", model.details["input_schema"]["properties"])

        # Verify accelerator enum
        accelerator_prop = model.details["input_schema"]["properties"]["accelerator"]
        self.assertIn("enum", accelerator_prop)
        self.assertIn("T4", accelerator_prop["enum"])
        self.assertIn("A100_80GB", accelerator_prop["enum"])

    def test_no_regeneration_if_schema_exists(self):
        """Test that existing custom schema is not overwritten"""
        existing_input_schema = {
            "type": "object",
            "properties": {"custom_field": {"type": "string"}},
        }

        model = self.model_model.create(
            {
                "name": "test-comfyicu-custom",
                "provider_id": self.provider.id,
                "model_use": "image_generation",
                "details": {"input_schema": existing_input_schema},
            }
        )

        # Verify existing schema was not overwritten
        self.assertEqual(model.details["input_schema"], existing_input_schema)
        self.assertIn("custom_field", model.details["input_schema"]["properties"])
        # Should NOT have default ComfyICU fields
        self.assertNotIn("accelerator", model.details["input_schema"]["properties"])

    def test_schema_generation_on_model_use_change(self):
        """Test schema generation when model_use changes to image_generation"""
        # Create as chat model first
        model = self.model_model.create(
            {
                "name": "test-comfyicu-change",
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
        self.assertIn("accelerator", model.details["input_schema"]["properties"])

    def test_schema_for_generic_generation(self):
        """Test schema generation works for model_use='generation' too"""
        model = self.model_model.create(
            {
                "name": "test-comfyicu-generic",
                "provider_id": self.provider.id,
                "model_use": "generation",  # Generic generation
                "details": {},
            }
        )

        # Verify schema was generated
        self.assertTrue(model.details.get("input_schema"))
        self.assertTrue(model.details.get("output_schema"))
        self.assertIn("prompt", model.details["input_schema"]["properties"])
        self.assertIn("accelerator", model.details["input_schema"]["properties"])
