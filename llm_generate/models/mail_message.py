import base64
import logging
import os
from datetime import datetime
from urllib.parse import urlparse

import requests
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class MailMessage(models.Model):
    _inherit = "mail.message"

    generation_inputs = fields.Text(
        string="Media Generation Inputs",
        readonly=True,
        copy=False,
        help="JSON string of inputs used for media generation, if this message initiated such a request.",
    )

    def is_llm_user_media_gen_message(self):
        if self.is_llm_user_message():
            result = bool(self.generation_inputs)
            return result
        return False

    @api.model
    def create_message_from_media_gen_stream(
            self, thread, stream, subtype_xmlid, placeholder_text="Generated media:"
    ):
        """
        thread: the llm.thread record
        stream: iterator of provider media gen method response
        subtype_xmlid: assistant vs tool result XMLID

        Yields UI events, and finally returns the full message record.
        """
        msg = None

        for chunk in stream:
            if msg is None and chunk.get("content"):
                generated_medias = thread.model_id.format_generation_response(
                    chunk["content"],
                )
                attachment_ids, media_urls = self.process_generated_medias(
                    generated_medias,
                    download_urls=True,
                )
                msg = thread._post_message(
                    subtype_xmlid=subtype_xmlid,
                    body=placeholder_text,
                    author_id=False,
                    attachment_ids=attachment_ids,
                )

                self.env["ir.attachment"].browse(attachment_ids).write({'res_id': msg.id})

                yield {"type": "message_create", "message": msg.message_format()[0]}
                return

        return msg

    def process_generated_medias(self, generated_medias, download_urls=False):
        """
        Process a list of media strings (URLs or base64) and return appropriate attachments

        Args:
            generated_medias: List of strings (URLs or base64 data)
            download_urls: Whether to download URL content and store as attachments (default: False)

        Returns:
            tuple: (attachment_ids, media_urls)
        """
        attachment_ids = []
        media_urls = []

        for media in generated_medias:
            if media.startswith(("http://", "https://")):
                if download_urls:
                    attachment_id = self._create_attachment_from_url(media)
                    if attachment_id:
                        attachment_ids.append(attachment_id)
                    else:
                        media_urls.append(media)
                else:
                    media_urls.append(media)
            else:
                # Assume it's base64 data, create an attachment
                attachment = self.env["ir.attachment"].create(
                    {
                        "name": "Generated Media",
                        "type": "binary",
                        "datas": media,
                        "res_model": self._name,
                        "res_id": self.id,
                    }
                )
                attachment_ids.append(attachment.id)

        return attachment_ids, media_urls

    def _create_attachment_from_url(self, url):
        """
        Download content from URL and create an attachment

        Args:
            url: URL to download content from

        Returns:
            int: attachment ID if successful, False otherwise
        """
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                # Try to get filename from URL or use generic name
                filename = os.path.basename(urlparse(url).path)

                # Add timestamp to ensure uniqueness

                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

                # Extract file extension if present
                name_parts = os.path.splitext(filename)
                if name_parts[0]:
                    # If we have a valid filename, add timestamp before extension
                    filename = f"{name_parts[0]}_{timestamp}{name_parts[1]}"
                else:
                    # If no valid filename, use generic name with timestamp
                    filename = f"media_{timestamp}"

                # Create attachment with binary data
                attachment = self.env["ir.attachment"].create(
                    {
                        "name": filename,
                        "type": "binary",
                        "mimetype": response.headers.get('Content-Type', None),
                        "datas": base64.b64encode(response.content),
                        "res_model": self._name,
                        "res_id": self.id,
                        "url": url,  # Store original URL for reference
                    }
                )
                return attachment.id
            else:
                _logger.warning(
                    f"Failed to download media from URL {url}: HTTP status {response.status_code}"
                )
                return False
        except Exception as e:
            _logger.warning(f"Failed to download media from URL {url}: {e}")
            return False

    def _get_llm_message_format_fields(self):
        """Extend the list of fields fetched by the base message_format."""
        fields_list = super()._get_llm_message_format_fields()
        fields_list.extend(
            [
                "generation_inputs",
            ]
        )
        return fields_list
