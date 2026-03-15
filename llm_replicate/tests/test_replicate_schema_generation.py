from odoo.tests.common import TransactionCase


class TestReplicateSchemaGeneration(TransactionCase):
    """Test Replicate-specific I/O schema generation"""

    def setUp(self):
        super().setUp()
        self.provider_model = self.env["llm.provider"]
        self.model_model = self.env["llm.model"]

        # Create test provider
        self.provider = self.provider_model.create(
            {
                "name": "Test Replicate Provider",
                "service": "replicate",
            }
        )

    def test_schema_generation_on_create_with_openapi(self):
        """Test schema generation when model is created with OpenAPI schema"""
        test_openapi_schema = {
            "components": {
                "schemas": {
                    "Input": {
                        "type": "object",
                        "properties": {
                            "prompt": {"type": "string", "description": "Image prompt"},
                            "width": {"type": "integer", "default": 512},
                        },
                        "required": ["prompt"],
                    },
                    "Output": {
                        "type": "array",
                        "items": {"type": "string", "format": "uri"},
                    },
                }
            }
        }

        model = self.model_model.create(
            {
                "name": "test/image-generator",
                "provider_id": self.provider.id,
                "model_use": "image_generation",
                "details": {"latest_version": {"openapi_schema": test_openapi_schema}},
            }
        )

        # Verify schema was generated
        self.assertTrue(model.details.get("input_schema"))
        self.assertTrue(model.details.get("output_schema"))
        self.assertEqual(model.details["input_schema"]["type"], "object")
        self.assertEqual(model.details["input_schema"]["additionalProperties"], False)
        self.assertIn("prompt", model.details["input_schema"]["properties"])
        self.assertIn("width", model.details["input_schema"]["properties"])

    def test_schema_generation_on_write(self):
        """Test schema generation when OpenAPI details are added via write"""
        # Create model without OpenAPI schema
        model = self.model_model.create(
            {
                "name": "test/model-write",
                "provider_id": self.provider.id,
                "model_use": "image_generation",
                "details": {},
            }
        )

        # Verify no schema yet
        self.assertFalse(model.details and model.details.get("input_schema"))

        # Add OpenAPI schema via write
        test_openapi_schema = {
            "components": {
                "schemas": {
                    "Input": {
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
                    },
                    "Output": {"type": "string"},
                }
            }
        }

        model.write(
            {"details": {"latest_version": {"openapi_schema": test_openapi_schema}}}
        )

        # Verify schema was generated
        self.assertTrue(model.details.get("input_schema"))
        self.assertTrue(model.details.get("output_schema"))
        self.assertIn("text", model.details["input_schema"]["properties"])

    def test_no_regeneration_if_schema_exists(self):
        """Test that existing schema is not overwritten"""
        existing_input_schema = {
            "type": "object",
            "properties": {"custom_field": {"type": "string"}},
        }

        model = self.model_model.create(
            {
                "name": "test/no-regen",
                "provider_id": self.provider.id,
                "model_use": "image_generation",
                "details": {
                    "latest_version": {
                        "openapi_schema": {
                            "components": {"schemas": {"Input": {}, "Output": {}}}
                        }
                    },
                    "input_schema": existing_input_schema,
                },
            }
        )

        # Verify existing schema was not overwritten
        self.assertEqual(model.details["input_schema"], existing_input_schema)
        self.assertIn("custom_field", model.details["input_schema"]["properties"])

    def test_no_schema_generation_without_openapi(self):
        """Test that no schema is generated if OpenAPI schema is missing"""
        model = self.model_model.create(
            {
                "name": "test/no-openapi",
                "provider_id": self.provider.id,
                "model_use": "image_generation",
                "details": {"some_other_field": "value"},
            }
        )

        # Verify no schema was generated
        self.assertFalse(model.details.get("input_schema"))
        self.assertFalse(model.details.get("output_schema"))

    def test_schema_generation_for_generic_generation(self):
        """Test schema generation works for model_use='generation' too"""
        test_openapi_schema = {
            "components": {
                "schemas": {
                    "Input": {
                        "type": "object",
                        "properties": {"input": {"type": "string"}},
                    },
                    "Output": {"type": "string"},
                }
            }
        }

        model = self.model_model.create(
            {
                "name": "test/generic-gen",
                "provider_id": self.provider.id,
                "model_use": "generation",  # Generic generation, not image_generation
                "details": {"latest_version": {"openapi_schema": test_openapi_schema}},
            }
        )

        # Verify schema was generated
        self.assertTrue(model.details.get("input_schema"))
        self.assertTrue(model.details.get("output_schema"))
