from odoo.exceptions import UserError
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

    def test_parse_model_extracts_named_openapi_refs(self):
        raw_model = {
            "endpoint_id": "fal-ai/bytedance/seedance/v1/pro/image-to-video",
            "metadata": {
                "category": "image-to-video",
                "description": "Image to video",
            },
            "openapi": {
                "paths": {
                    "/model": {
                        "post": {
                            "requestBody": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "$ref": "#/components/schemas/SeedanceInput"
                                        }
                                    }
                                },
                                "required": True,
                            },
                            "responses": {
                                "200": {
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "$ref": "#/components/schemas/QueueStatus"
                                            }
                                        }
                                    }
                                }
                            },
                        }
                    },
                    "/model/requests/{request_id}": {
                        "get": {
                            "responses": {
                                "200": {
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "$ref": "#/components/schemas/SeedanceOutput"
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                },
                "components": {
                    "schemas": {
                        "QueueStatus": {"type": "object"},
                        "SeedanceInput": {
                            "type": "object",
                            "required": ["prompt", "image_url"],
                            "properties": {
                                "prompt": {"type": "string"},
                                "image_url": {"type": "string"},
                            },
                        },
                        "SeedanceOutput": {
                            "type": "object",
                            "properties": {"video": {"type": "object"}},
                        },
                    }
                },
            },
        }

        parsed = self.provider._fal_ai_parse_model(raw_model)

        input_schema = parsed["details"]["input_schema"]
        output_schema = parsed["details"]["output_schema"]
        self.assertEqual(input_schema["required"], ["prompt", "image_url"])
        self.assertIn("image_url", input_schema["properties"])
        self.assertIn("video", output_schema["properties"])

    def test_resolve_inputs_uses_openapi_schema_fallback(self):
        model = self.env["llm.model"].create({
            "name": "fal-ai/bytedance/seedance/v1/pro/image-to-video",
            "provider_id": self.provider.id,
            "model_use": "generation",
            "details": {
                "openapi": {
                    "paths": {
                        "/model": {
                            "post": {
                                "requestBody": {
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "$ref": "#/components/schemas/SeedanceInput"
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "components": {
                        "schemas": {
                            "SeedanceInput": {
                                "type": "object",
                                "required": ["prompt", "image_url"],
                                "properties": {
                                    "prompt": {"type": "string"},
                                    "image_url": {"type": "string"},
                                },
                            }
                        }
                    },
                }
            },
        })

        resolved = self.provider._fal_ai_resolve_inputs(
            {"image": "https://example.com/image.jpg", "prompt": "make it move"},
            model,
        )

        self.assertEqual(resolved["image_url"], "https://example.com/image.jpg")
        self.assertNotIn("image", resolved)

    def test_validate_inputs_fails_before_fal_api_when_prompt_missing(self):
        model = self.env["llm.model"].create({
            "name": "fal-ai/bytedance/seedance/v1/pro/image-to-video",
            "provider_id": self.provider.id,
            "model_use": "generation",
            "details": {
                "input_schema": {
                    "type": "object",
                    "required": ["prompt", "image_url"],
                    "properties": {
                        "prompt": {"type": "string"},
                        "image_url": {"type": "string"},
                    },
                }
            },
        })

        with self.assertRaisesRegex(UserError, "prompt"):
            self.provider._fal_ai_validate_inputs({"image_url": "x"}, model)
