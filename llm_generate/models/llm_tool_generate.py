import logging
from typing import Any

from odoo import api, models

_logger = logging.getLogger(__name__)


class LLMToolGenerate(models.Model):
    _inherit = "llm.tool"

    @api.model
    def _get_available_implementations(self):
        implementations = super()._get_available_implementations()
        return implementations + [("odoo_generate", "Odoo Media Generator")]

    def odoo_generate_execute(
            self, model_id: int, inputs: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate an image using the specified model and prompt.

        Parameters:
            model_id: The ID of the llm.model to use for generation
            inputs: The dictionary to generate an image from based on model's input schema

        Returns:
            A dictionary with the generated image URLs and markdown
        """
        self.ensure_one()

        model = self.env["llm.model"].browse(int(model_id))
        if not model.exists():
            return {"error": f"Model with ID {model_id} not found"}

        if model.model_use != "image_generation":
            return {
                "error": f"Model {model.name} is not configured for image generation"
            }
        result = model.generate_media(inputs, stream=False)

        if isinstance(result, list):
            image_urls = result
        else:
            image_urls = [result]

        markdown_images = []
        for i, url in enumerate(image_urls):
            markdown_images.append(f"![Generated Image {i + 1}]({url})")

        return {
            "success": True,
            "image_urls": image_urls,
            "markdown": "\n".join(markdown_images),
        }
