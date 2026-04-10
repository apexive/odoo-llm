import base64
from typing import Any

from odoo import _, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.llm.models.mail_message import AUDIO_MIMETYPES


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def transcribe_attachments(
        self,
        model,
        attachment_ids: list[int],
        prompt: str | None = None,
        language: str | None = None,
    ) -> list[dict[str, Any]]:
        """Transcribe multiple audio attachments with the selected model."""
        model = self._get_transcription_model(model)

        results = []
        for attachment_id in attachment_ids:
            try:
                attachment = self.browse(int(attachment_id))
                if not attachment.exists():
                    raise ValidationError(
                        _("Attachment with ID %s was not found.") % attachment_id
                    )

                results.append(
                    self._transcribe_attachment(
                        attachment=attachment,
                        model=model,
                        prompt=prompt,
                        language=language,
                    )
                )
            except Exception as exc:
                results.append(
                    {
                        "attachment_id": attachment_id,
                        "error": str(exc),
                    }
                )
        return results

    def _get_transcription_model(self, model):
        if isinstance(model, int):
            model = self.env["llm.model"].browse(model)

        if not model or not model.exists():
            raise UserError(_("A valid transcription model is required."))
        if not model.active:
            raise UserError(_("Model '%s' is inactive.") % model.name)
        if model.model_use != "transcription":
            raise UserError(
                _("Model '%s' is not a transcription model.") % model.name
            )
        if not model.provider_id.active:
            raise UserError(
                _("Provider '%s' is inactive.") % model.provider_id.name
            )
        return model

    def _transcribe_attachment(self, attachment, model, prompt=None, language=None):
        mimetype = attachment.mimetype
        normalized_mimetype = (mimetype or "").split(";", 1)[0].strip().lower()

        if normalized_mimetype not in AUDIO_MIMETYPES:
            raise ValidationError(
                _(
                    "Attachment '%(name)s' is not a supported audio file (mimetype: %(mimetype)s)."
                )
                % {
                    "name": attachment.name,
                    "mimetype": mimetype or _("missing"),
                }
            )

        if not attachment.datas:
            raise ValidationError(
                _("Attachment '%s' has no binary content.") % attachment.name
            )

        audio_bytes = base64.b64decode(attachment.datas)
        transcript = model.transcribe_audio(
            data=audio_bytes,
            filename=attachment.name or "audio.bin",
            mimetype=normalized_mimetype,
            prompt=prompt,
            language=language,
        )

        return {
            "attachment_id": attachment.id,
            "attachment_name": attachment.name,
            "mimetype": normalized_mimetype,
            "provider": model.provider_id.service,
            "model": transcript.get("model"),
            "language": transcript.get("language"),
            "duration": transcript.get("duration"),
            "transcript": transcript.get("text", ""),
        }
