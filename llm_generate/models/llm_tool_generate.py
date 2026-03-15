from typing import Any

from odoo import api, models
from odoo.exceptions import UserError


class LLMToolGenerate(models.Model):
    _inherit = "llm.tool"

    @api.model
    def _get_available_implementations(self):
        implementations = super()._get_available_implementations()
        return implementations + [("odoo_generate", "Odoo Content Generator")]

    def odoo_generate_execute(
        self, model_id: int, inputs: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate content using the specified model and inputs."""
        self.ensure_one()

        model = self.env["llm.model"].browse(int(model_id))
        if not model.exists():
            raise UserError(f"Model with ID {model_id} not found")

        # Use model's generate method - returns tuple (output_data, urls)
        output_data, urls = model.generate(inputs)

        # Get the existing tool message from context
        tool_message = self.env.context.get("message")

        # Use message method to process URLs and create attachments
        markdown_content, attachments = tool_message.process_generation_urls(urls)

        return {
            "success": True,
            "output_data": output_data,
            "urls": [
                {"url": att.url, "content_type": att.mimetype} for att in attachments
            ],
            "markdown": markdown_content,
            "content_count": len(urls),
        }
