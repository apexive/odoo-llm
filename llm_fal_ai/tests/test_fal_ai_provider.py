from odoo.tests.common import TransactionCase


class TestFalAIProvider(TransactionCase):
    def setUp(self):
        super().setUp()
        self.provider = self.env["llm.provider"].create(
            {
                "name": "Test Fal.ai",
                "service": "fal_ai",
                "api_key": "test-key",
            }
        )

    def test_category_mapping_for_image_model(self):
        capabilities = self.provider._fal_ai_capabilities_from_category(
            "text-to-image", "fal-ai/flux/dev"
        )
        self.assertEqual(capabilities, ["image_generation"])

    def test_category_mapping_for_video_model(self):
        capabilities = self.provider._fal_ai_capabilities_from_category(
            "text-to-video", "fal-ai/wan/v2.2-a14b/text-to-video"
        )
        self.assertEqual(capabilities, ["generation"])

    def test_parse_model_extracts_openapi_schemas(self):
        raw_model = {
            "endpoint_id": "fal-ai/flux/dev",
            "metadata": {
                "category": "text-to-image",
                "description": "Fast text-to-image generation",
            },
            "openapi": {
                "components": {
                    "schemas": {
                        "Input": {"type": "object", "properties": {"prompt": {"type": "string"}}},
                        "Output": {"type": "array", "items": {"type": "string"}},
                    }
                }
            },
        }

        parsed = self.provider._fal_ai_parse_model(raw_model)

        self.assertEqual(parsed["name"], "fal-ai/flux/dev")
        self.assertEqual(parsed["details"]["capabilities"], ["image_generation"])
        self.assertEqual(parsed["details"]["category"], "text-to-image")
        self.assertIn("input_schema", parsed["details"])
        self.assertIn("output_schema", parsed["details"])
