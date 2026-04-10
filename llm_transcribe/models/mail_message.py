from odoo import models


class MailMessage(models.Model):
    _inherit = "mail.message"

    @staticmethod
    def format_transcription_results(results):
        parts = []
        for result in results:
            if result.get("error"):
                label = (
                    result.get("attachment_name")
                    or result.get("attachment_id")
                    or "Attachment"
                )
                parts.append(f"### {label}\n\nError: {result['error']}")
                continue

            label = result.get("attachment_name") or "Audio"
            transcript = result.get("transcript") or ""
            parts.append(f"### {label}\n\n{transcript}")
        return "\n\n".join(parts)

    def process_transcription_results(self, results):
        self.ensure_one()
        return self.format_transcription_results(results)
