import base64
import logging

from odoo import _, api, fields, models, tools

_logger = logging.getLogger(__name__)

IMAGE_MIMETYPES = (
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
)

# Magic bytes for image type detection
IMAGE_MAGIC_BYTES = {
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
    b"RIFF": "image/webp",  # RIFF....WEBP
}

PDF_MIMETYPES = ("application/pdf",)

# Audio mimetypes - only supported by OpenAI gpt-4o-audio-preview models
AUDIO_MIMETYPES = (
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/ogg",
    "audio/flac",
    "audio/webm",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
)

# Video mimetypes - NOT supported by any LLM provider
VIDEO_MIMETYPES = (
    "video/mp4",
    "video/webm",
    "video/quicktime",
    "video/x-msvideo",
    "video/x-matroska",
    "video/ogg",
)

# Office document mimetypes - NOT supported via chat API
OFFICE_MIMETYPES = (
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
)

TEXT_MIMETYPES = (
    "text/plain",
    "text/markdown",
    "text/csv",
    "text/html",
    "text/css",
    "text/javascript",
    "text/xml",
    "text/x-python",
    "application/json",
    "application/xml",
    "application/javascript",
    "application/x-python-code",
)

SUPPORTED_IMAGE_MIMETYPES = IMAGE_MIMETYPES


def _detect_image_mimetype(raw_bytes):
    """Detect the real image mimetype from magic bytes.

    Args:
        raw_bytes: The raw image bytes

    Returns:
        The detected mimetype or None if not recognized
    """
    for magic, mimetype in IMAGE_MAGIC_BYTES.items():
        if raw_bytes.startswith(magic):
            # Special check for WebP: must have WEBP after RIFF header
            if magic == b"RIFF" and len(raw_bytes) >= 12:
                if raw_bytes[8:12] != b"WEBP":
                    continue
            return mimetype
    return None


def _detect_audio_format(raw_bytes):
    """Detect audio format from magic bytes for OpenAI API.

    Args:
        raw_bytes: The raw audio bytes

    Returns:
        The format string for OpenAI API (wav, mp3, flac, ogg) or None
    """
    # WAV: RIFF....WAVE
    if raw_bytes[:4] == b"RIFF" and len(raw_bytes) >= 12:
        if raw_bytes[8:12] == b"WAVE":
            return "wav"
    # MP3: ID3 tag or sync bytes
    if raw_bytes[:3] == b"ID3" or raw_bytes[:2] == b"\xff\xfb":
        return "mp3"
    # FLAC
    if raw_bytes[:4] == b"fLaC":
        return "flac"
    # OGG
    if raw_bytes[:4] == b"OggS":
        return "ogg"
    # M4A/MP4 audio
    if raw_bytes[4:8] == b"ftyp":
        return "mp4"
    return None


class MailMessage(models.Model):
    _inherit = "mail.message"

    LLM_XMLIDS = (
        "llm.mt_tool",
        "llm.mt_user",
        "llm.mt_assistant",
        "llm.mt_system",
    )

    llm_role = fields.Char(
        string="LLM Role",
        compute="_compute_llm_role",
        store=True,
        index=True,  # Add index for better query performance
        help="The LLM role for this message (user, assistant, tool, system)",
    )

    is_error = fields.Boolean(
        string="Is Error Message",
        default=False,
        index=True,
        help="Error messages are shown to users but excluded from LLM context",
    )

    body_json = fields.Json(
        string="JSON Body",
        help="JSON data for tool messages and other structured content",
    )

    @api.depends("subtype_id")
    def _compute_llm_role(self):
        """Compute the LLM role for messages based on their subtype."""
        id_to_role, _ = self.get_llm_roles()

        for message in self:
            if message.subtype_id and message.subtype_id.id in id_to_role:
                message.llm_role = id_to_role[message.subtype_id.id]
            else:
                message.llm_role = False

    @tools.ormcache()
    def get_llm_roles(self):
        """Get cached mapping of LLM subtype IDs to clean role names and vice versa.

        Returns:
            tuple: (id_to_role_dict, role_to_id_dict) where:
                - id_to_role_dict: {subtype_id: 'user', subtype_id: 'assistant', ...}
                - role_to_id_dict: {'user': subtype_id, 'assistant': subtype_id, ...}
        """
        id_to_role = {}
        role_to_id = {}

        for xmlid in self.LLM_XMLIDS:
            subtype_id = self.env["ir.model.data"]._xmlid_to_res_id(
                xmlid,
                raise_if_not_found=False,
            )
            if subtype_id:
                # Extract clean role name (e.g., 'user' from 'llm.mt_user')
                role = xmlid.split(".")[-1][3:]  # Remove 'mt_' prefix
                id_to_role[subtype_id] = role
                role_to_id[role] = subtype_id

        return id_to_role, role_to_id

    def get_llm_role(self):
        """Get the LLM role for this message (ensure_one).

        DEPRECATED: Use the llm_role computed field instead.

        Returns:
            str or False: The role name ('user', 'assistant', 'tool', 'system') or False if not an LLM message
        """
        self.ensure_one()
        return self.llm_role

    def is_llm_message(self):
        """Check if messages are LLM messages using the stored field."""
        return {message: bool(message.llm_role) for message in self}

    def is_llm_user_message(self):
        """Check if messages are LLM user messages using the stored field."""
        return {message: message.llm_role == "user" for message in self}

    def is_llm_assistant_message(self):
        """Check if messages are LLM assistant messages using the stored field."""
        return {message: message.llm_role == "assistant" for message in self}

    def is_llm_tool_message(self):
        """Check if messages are LLM tool messages using the stored field."""
        return {message: message.llm_role == "tool" for message in self}

    def is_llm_system_message(self):
        """Check if messages are LLM system messages using the stored field."""
        return {message: message.llm_role == "system" for message in self}

    def _check_llm_role(self, role):
        """Check if messages match a specific LLM role using the stored field.

        Args:
            role (str): The role name ('user', 'assistant', 'tool', 'system')
        """
        return {message: message.llm_role == role for message in self}

    def to_store_format(self):
        """Convert message to store format compatible with Odoo 18.0. Used by frontend js components"""
        self.ensure_one()
        from odoo.addons.mail.tools.discuss import Store

        store = Store()
        self._to_store(store)
        result = store.get_result()

        return result["mail.message"][0]

    def _get_attachments_by_mimetype(self, mimetypes):
        """Get attachments filtered by mimetype.

        Base method for DRY attachment extraction. Returns raw attachment records
        filtered by the given mimetypes and having data.

        Args:
            mimetypes: Tuple of mimetype strings to filter by

        Returns:
            Filtered ir.attachment recordset
        """
        self.ensure_one()
        return self.attachment_ids.filtered(
            lambda att: att.mimetype and att.mimetype in mimetypes and att.datas,
        )

    # Max pixel dimension when sending images to the LLM for vision/understanding.
    # Does NOT affect the original attachment — generation providers (fal.ai, Replicate)
    # always receive the original binary via _resolve_attachment_inputs.
    _LLM_IMAGE_MAX_PX = 1568

    def _get_image_attachments(self):
        """Get image attachments with validated mimetype from magic bytes.

        Returns list of dicts with mimetype (validated), data (base64), and name.
        The mimetype is detected from the actual image content, not from Odoo's
        stored mimetype, to ensure compatibility with strict API validators
        like Anthropic Claude.

        Images are downsampled to _LLM_IMAGE_MAX_PX on the longest side before
        encoding. A 3 MB WhatsApp photo is otherwise ~700K tokens as base64.
        """
        images = []
        for att in self._get_attachments_by_mimetype(SUPPORTED_IMAGE_MIMETYPES):
            try:
                raw_bytes = base64.b64decode(att.datas)
                real_mimetype = _detect_image_mimetype(raw_bytes)
                used_mimetype = real_mimetype or att.mimetype

                if real_mimetype and real_mimetype != att.mimetype:
                    _logger.debug(
                        "Image %s: correcting mimetype from %s to %s",
                        att.name,
                        att.mimetype,
                        real_mimetype,
                    )

                raw_bytes, used_mimetype = self._llm_resize_image(
                    raw_bytes, used_mimetype, att.name
                )
                images.append(
                    {
                        "mimetype": used_mimetype,
                        "data": base64.b64encode(raw_bytes).decode("utf-8"),
                        "name": att.name or "image",
                    },
                )
            except (ValueError, TypeError) as e:
                _logger.warning(
                    "Failed to process image attachment %s: %s",
                    att.name,
                    e,
                )
        return images

    def _llm_resize_image(self, raw_bytes, mimetype, name="image"):
        """Downsample image so its longest side is at most _LLM_IMAGE_MAX_PX.

        Returns (raw_bytes, mimetype) unchanged if PIL is unavailable or the
        image is already within bounds.
        """
        try:
            import io
            from PIL import Image

            img = Image.open(io.BytesIO(raw_bytes))
            if max(img.size) <= self._LLM_IMAGE_MAX_PX:
                return raw_bytes, mimetype

            scale = self._LLM_IMAGE_MAX_PX / max(img.size)
            new_size = (int(img.width * scale), int(img.height * scale))
            img = img.resize(new_size, Image.LANCZOS)

            if img.mode in ("RGBA", "LA"):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[-1])
                img = bg
            elif img.mode != "RGB":
                img = img.convert("RGB")

            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=82, optimize=True)
            resized = buf.getvalue()
            _logger.debug(
                "Image %s resized to %s, %.0f KB → %.0f KB",
                name, new_size, len(raw_bytes) / 1024, len(resized) / 1024,
            )
            return resized, "image/jpeg"
        except Exception as e:
            _logger.warning("_llm_resize_image failed for %s, using original: %s", name, e)
            return raw_bytes, mimetype

    def _get_pdf_attachments(self):
        """Get PDF attachments as base64 data."""
        return [
            {
                "mimetype": att.mimetype,
                "data": att.datas.decode("utf-8"),
                "name": att.name or "document.pdf",
            }
            for att in self._get_attachments_by_mimetype(PDF_MIMETYPES)
        ]

    def _get_text_attachments(self):
        """Get text attachments with decoded content."""
        texts = []
        for att in self._get_attachments_by_mimetype(TEXT_MIMETYPES):
            try:
                raw_data = base64.b64decode(att.datas)
                content = raw_data.decode("utf-8")
                texts.append(
                    {
                        "mimetype": att.mimetype,
                        "content": content,
                        "name": att.name or "file.txt",
                    },
                )
            except (UnicodeDecodeError, ValueError) as e:
                _logger.warning("Failed to decode text attachment %s: %s", att.name, e)
        return texts

    def _get_audio_attachments(self):
        """Get audio attachments with detected format for OpenAI API.

        Returns list of dicts with format (wav, mp3, etc.), data (base64), and name.
        Only for use with OpenAI gpt-4o-audio-preview models.
        """
        audios = []
        for att in self._get_attachments_by_mimetype(AUDIO_MIMETYPES):
            try:
                raw_bytes = base64.b64decode(att.datas)
                audio_format = _detect_audio_format(raw_bytes)
                if audio_format:
                    audios.append(
                        {
                            "format": audio_format,
                            "data": att.datas.decode("utf-8"),
                            "name": att.name or "audio",
                        },
                    )
                else:
                    _logger.warning("Could not detect audio format for %s", att.name)
            except (ValueError, TypeError) as e:
                _logger.warning(
                    "Failed to process audio attachment %s: %s",
                    att.name,
                    e,
                )
        return audios

    def _get_unsupported_attachments(
        self,
        provider_service,
        is_multimodal=False,
    ):
        """Get list of attachments not supported by the current provider/model.

        This method supports both single messages and recordsets, which is essential
        for validating the ENTIRE conversation context before sending to the LLM.

        Why check the full context?
        ---------------------------
        When a user switches LLM models mid-conversation, previously valid attachments
        may become incompatible. For example:
        - User sends image to multimodal model → works
        - User switches to text-only model → images in context unsupported

        Supported file types:
        - Images (JPEG, PNG, GIF, WebP) - requires multimodal model
        - PDFs - requires multimodal model
        - Text files (plain text, markdown, code) - always supported

        Unsupported (user is notified, file skipped):
        - Audio files - not yet implemented
        - Video files - not supported by any LLM
        - Office documents (Word, Excel, PPT) - must convert to PDF first

        The notification message has is_error=True so it's excluded from
        future LLM context, allowing the conversation to continue normally.

        Args:
            provider_service: The provider service name (e.g., 'anthropic', 'openai')
            is_multimodal: Whether the model supports images/PDFs

        Returns:
            List of dicts with name, mimetype, and reason for each unsupported attachment
        """
        unsupported = []

        for message in self:
            for att in message.attachment_ids:
                if not att.mimetype or not att.datas:
                    continue

                mimetype = att.mimetype
                reason = None

                # Video - never supported by any LLM
                if mimetype in VIDEO_MIMETYPES:
                    reason = _("Video files are not supported")

                # Office documents - must convert to PDF
                elif mimetype in OFFICE_MIMETYPES:
                    reason = _("Office documents must be converted to PDF first")

                # Audio - not yet implemented
                elif mimetype in AUDIO_MIMETYPES:
                    reason = _("Audio files are not yet supported")

                # Images/PDFs - only with multimodal models
                elif mimetype in IMAGE_MIMETYPES and not is_multimodal:
                    reason = _("This model does not support images")

                elif mimetype in PDF_MIMETYPES and not is_multimodal:
                    reason = _("This model does not support PDFs")

                if reason:
                    unsupported.append(
                        {
                            "name": att.name,
                            "mimetype": mimetype,
                            "reason": reason,
                        },
                    )

        return unsupported
