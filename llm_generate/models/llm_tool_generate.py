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
        """Generate media using the specified model and inputs.

        Parameters:
            model_id: The ID of the llm.model to use for generation
            inputs: The dictionary to generate media from based on model's input schema

        Returns:
            A dictionary with the generated media URLs and markdown
        """
        self.ensure_one()

        model = self.env["llm.model"].browse(int(model_id))
        if not model.exists():
            return {"error": f"Model with ID {model_id} not found"}

        if not model._is_media_generation_model():
            return {
                "error": f"Model {model.name} is not configured for media generation"
            }

        try:
            # Generate media using the model
            media_urls = next(model.generate_media(inputs, stream=False))['content']

            # Check if we have a message in context for processing attachments
            context_message = self.env.context.get('message')
            attachment_ids = []

            if context_message:
                _logger.info(f"Processing generated media for message {context_message.id}")

                attachment_ids, remaining_urls = context_message.process_generated_medias(
                    media_urls, download_urls=True
                )

            # Generate markdown for display
            markdown_images = []
            for i, url in enumerate(media_urls):
                markdown_images.append(f"![Generated Media {i+1}]({url})")

            result = {
                "success": True,
                "media_urls": media_urls,
                "markdown": "\n".join(markdown_images),
            }

            # Add attachment info if we processed any
            if context_message and attachment_ids:
                result["attachments_created"] = len(attachment_ids)
                result["attachment_ids"] = attachment_ids

            return result

        except Exception as e:
            _logger.error(f"Error in media generation: {e}")
            return {
                "error": f"Media generation failed: {str(e)}",
                "success": False
            }
