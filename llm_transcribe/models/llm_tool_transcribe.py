import json
from typing import Any

from odoo import api, models
from odoo.exceptions import UserError


class LLMToolTranscribe(models.Model):
    _inherit = "llm.tool"

    @api.model
    def _get_available_implementations(self):
        implementations = super()._get_available_implementations()
        return implementations + [("odoo_transcribe", "Odoo Audio Transcriber")]

    def odoo_transcribe_execute(
        self, model_id: int, inputs: dict[str, Any]
    ) -> dict[str, Any]:
        """Transcribe audio using the specified model and structured inputs."""
        self.ensure_one()

        if isinstance(inputs, str):
            try:
                inputs = json.loads(inputs)
            except (ValueError, TypeError):
                pass

        if not isinstance(inputs, dict):
            raise UserError("inputs must be an object")

        model = self.env["llm.model"].browse(int(model_id))
        if not model.exists():
            raise UserError(f"Model with ID {model_id} not found")
        if model.model_use != "transcription":
            raise UserError(f"Model '{model.name}' is not a transcription model")

        attachment_ids = inputs.get("attachment_ids") or []
        if isinstance(attachment_ids, str):
            try:
                attachment_ids = json.loads(attachment_ids)
            except (ValueError, TypeError):
                attachment_ids = [attachment_ids]
        if not isinstance(attachment_ids, list) or not attachment_ids:
            raise UserError("inputs.attachment_ids must be a non-empty list")

        prompt = (inputs.get("prompt") or "").strip() or None
        language = (inputs.get("language") or "").strip() or None

        results = self.env["ir.attachment"].transcribe_attachments(
            model=model,
            attachment_ids=attachment_ids,
            prompt=prompt,
            language=language,
        )

        tool_message = self.env.context.get("message")
        markdown_content = (
            tool_message.process_transcription_results(results)
            if tool_message
            else self.env["mail.message"].format_transcription_results(results)
        )

        output_data = {
            "provider": model.provider_id.service,
            "model_name": model.name,
            "inputs": inputs,
            "num_results": len(results),
        }

        return {
            "success": True,
            "output_data": output_data,
            "results": results,
            "markdown": markdown_content,
            "content_count": len(results),
        }
