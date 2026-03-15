import base64
import logging
import mimetypes
import re
from urllib.parse import urljoin, urlparse

import requests
from markdownify import markdownify as md

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Regex to find meta refresh tags
# Handles single or double quotes around url and content values
META_REFRESH_RE = re.compile(
    r"""<meta[^>]*http-equiv\s*=\s*["']?refresh["']?[^>]*content\s*=\s*["']?\d+\s*;\s*url=([^"'>]+)["']?""",
    re.IGNORECASE | re.DOTALL,
)


class LLMResourceHTTPRetriever(models.Model):
    _inherit = "llm.resource"

    @api.model
    def _get_available_retrievers(self):
        """Get all available retriever methods"""
        retrievers = super()._get_available_retrievers()
        retrievers.append(("http", "HTTP Retriever"))
        return retrievers

    def retrieve_http(self, retrieval_details, record):
        """
        Implementation for HTTP retrieval when the attachment has an external URL
        """
        self.ensure_one()
        _logger.info("Retrieving HTTP resource: %s", retrieval_details)
        if retrieval_details["type"] == "url":
            return self._http_retrieve(retrieval_details, record)
        else:
            return False

    def _ensure_full_urls(self, markdown_content, base_url):
        """
        Ensure all links in markdown content have full URLs.

        :param markdown_content: Markdown content to process
        :param base_url: Base URL to prepend to relative URLs
        :return: Markdown content with full URLs
        """
        # Regex to find markdown links: [text](url)
        link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"

        def replace_link(match):
            text = match.group(1)
            url = match.group(2)

            if not url.startswith(("http://", "https://", "mailto:", "tel:")):
                try:
                    full_url = urljoin(base_url, url)
                    return f"[{text}]({full_url})"
                except ValueError:
                    _logger.warning(
                        f"Could not join base URL '{base_url}' with relative URL '{url}'. Keeping relative link."
                    )
                    return match.group(0)
            return match.group(0)

        return re.sub(link_pattern, replace_link, markdown_content)

    def _is_text_content_type(self, content_type):
        """
        Check if the content type is a text type that can be processed directly.

        :param content_type: MIME type to check (e.g., 'text/html')
        :return: Boolean indicating if it's a text content type
        """
        text_types = [
            "text/html",
            "text/plain",
            "text/markdown",
            "application/xhtml+xml",
            "application/xml",
            "application/json",
            "application/javascript",
        ]
        main_type = content_type.split(";")[0].strip()
        return any(main_type.startswith(t) for t in text_types)

    # --- Refactored Helper Methods ---

    def _http_fetch_final_response(self, initial_url, headers, max_refreshes=1):
        """
        Fetches the final response after handling standard and meta redirects.

        :param initial_url: The starting URL
        :param headers: HTTP headers for the request
        :param max_refreshes: Maximum number of meta refreshes to follow
        :return: Tuple (final_response, final_url)
        :raises: requests.exceptions.RequestException on request failures
        """
        _logger.info(f"Fetching final response for URL: {initial_url}")
        response = requests.get(
            initial_url, timeout=30, headers=headers, allow_redirects=True
        )
        response.raise_for_status()

        current_url = response.url
        if current_url != initial_url:
            _logger.info(f"Initial URL '{initial_url}' redirected to '{current_url}'.")

        refreshes_followed = 0
        while refreshes_followed < max_refreshes:
            content_type_header = response.headers.get("Content-Type", "")
            content_type = content_type_header.split(";")[0].strip()

            if self._is_text_content_type(content_type):
                try:
                    content = response.content
                    temp_text_content = content.decode(
                        response.encoding or "utf-8", errors="ignore"
                    )
                    meta_match = META_REFRESH_RE.search(temp_text_content)

                    if meta_match:
                        refresh_target_relative = meta_match.group(1).strip()
                        refresh_target_absolute = urljoin(
                            current_url, refresh_target_relative
                        )
                        _logger.info(
                            f"Detected meta refresh. Following from '{current_url}' to '{refresh_target_absolute}'"
                        )

                        response = requests.get(
                            refresh_target_absolute,
                            timeout=30,
                            headers=headers,
                            allow_redirects=True,
                        )
                        response.raise_for_status()

                        new_current_url = response.url
                        if new_current_url != refresh_target_absolute:
                            _logger.info(
                                f"Meta refresh target '{refresh_target_absolute}' redirected to '{new_current_url}'."
                            )
                        current_url = new_current_url
                        refreshes_followed += 1
                        continue
                    else:
                        break
                except Exception as e:
                    _logger.warning(
                        f"Error during meta refresh check/follow for {current_url}: {e}"
                    )
                    break
            else:
                break  # Not text content, cannot contain meta refresh

        return response, current_url  # Return the latest response and URL

    def _http_determine_file_details(self, response, final_url):
        """
        Determines content type and filename for the fetched content.

        :param response: The final requests.Response object
        :param final_url: The final URL after all redirects
        :return: Dictionary {'content_type': str, 'filename': str}
        """
        content_type_header = response.headers.get("Content-Type", "")
        content_type = content_type_header.split(";")[0].strip()

        # Guess mime type if not provided or unclear
        if not content_type:
            content_type, _ = mimetypes.guess_type(final_url)
        if not content_type:
            _logger.warning(
                f"Could not determine mime type for {final_url}. Defaulting to octet-stream."
            )
            content_type = "application/octet-stream"

        parsed_url = urlparse(final_url)
        # Use attachment name if available, else try URL path, else default
        filename = self.name or parsed_url.path.split("/")[-1] or "downloaded_file"
        if "." not in filename:
            ext = mimetypes.guess_extension(content_type)
            if ext:
                filename += ext

        return {"content_type": content_type, "filename": filename}

    def _http_process_text(self, response, content, final_url):
        """
        Decodes text content, converts HTML to Markdown, and ensures absolute URLs.

        :param response: The final requests.Response object
        :param content: The raw byte content
        :param final_url: The final URL for resolving relative links
        :return: Dictionary {'markdown_content': str or None, 'decoded_successfully': bool}
        """
        try:
            # Decode using detected or fallback encodings
            text_content = content.decode(response.encoding or "utf-8")
            decoded_successfully = True
        except UnicodeDecodeError:
            _logger.warning(f"UTF-8 decoding failed for {final_url}. Trying fallbacks.")
            text_content = None
            for encoding in ["latin-1", "windows-1252", "iso-8859-1"]:
                try:
                    text_content = content.decode(encoding)
                    _logger.info(f"Successfully decoded {final_url} using {encoding}.")
                    decoded_successfully = True
                    break
                except UnicodeDecodeError:
                    continue
            if text_content is None:
                _logger.error(
                    f"Failed to decode content from {final_url} with any supported encoding."
                )
                decoded_successfully = False

        if decoded_successfully:
            content_type_header = response.headers.get("Content-Type", "")
            content_type = content_type_header.split(";")[0].strip()

            if "html" in content_type:
                try:
                    markdown_content = md(text_content)
                except Exception as e:
                    _logger.error(f"Markdownify conversion failed for {final_url}: {e}")
                    markdown_content = text_content  # Fallback to original text
            else:
                markdown_content = text_content

            markdown_content = self._ensure_full_urls(markdown_content, final_url)
            return {"markdown_content": markdown_content, "decoded_successfully": True}
        else:
            return {"markdown_content": None, "decoded_successfully": False}

    def _http_store_content(
        self,
        content,
        content_type,
        filename,
        retrieval_details,
        record,
    ):
        """
        Updates the ir.attachment record with the fetched content.

        :param content: Raw byte content
        :param content_type: Determined MIME type
        :param filename: Determined filename
        """

        target_fields = retrieval_details["target_fields"]

        target_field_type = record._fields[target_fields["content"]].type
        if target_fields["content"]:
            if target_field_type == "binary":
                content = base64.b64encode(content)
            record.write({target_fields["content"]: content})
        if target_fields.get("mimetype", None):
            record.write({target_fields["mimetype"]: content_type})
        if target_fields.get("filename", None):
            record.write({target_fields["filename"]: filename})
        if target_fields.get("type", None):
            record.write({target_fields["type"]: target_field_type})

    # --- Main Orchestrator Method ---

    def _http_retrieve(self, retrieval_details, record):
        """
        Retrieves content from an external URL, handling redirects and meta refreshes.
        Orchestrates fetching, processing, and storing the content.

        :param retrieval_details: The retrieval details dictionary
        :return: Dictionary with state or Boolean indicating success
        """
        self.ensure_one()
        _logger.info(f"Retrieving HTTP resource: {record.name}")
        field = retrieval_details["field"]

        initial_url = record[field]

        if not initial_url:
            self._post_styled_message(
                f"No URL found for this resource {record.name}", "error"
            )
            return False

        _logger.info(
            f"Starting HTTP retrieval for {record.name} from initial URL: {initial_url}"
        )
        headers = {"User-Agent": "Mozilla/5.0 (compatible; Odoo LLM Resource/1.0)"}

        final_response, final_url = self._http_fetch_final_response(
            initial_url, headers
        )

        file_details = self._http_determine_file_details(final_response, final_url)
        content_type = file_details["content_type"]
        filename = file_details["filename"]

        content = final_response.content

        if self._is_text_content_type(content_type):
            processing_result = self._http_process_text(
                final_response, content, final_url
            )

            if processing_result["decoded_successfully"]:
                markdown_content = processing_result["markdown_content"]
                self.write({"content": markdown_content})
                self._http_store_content(
                    content, content_type, filename, retrieval_details, record
                )
                self._post_styled_message(
                    f"Successfully retrieved and processed text content from URL: {final_url}({len(markdown_content)} characters) (original: {initial_url})",
                    "success",
                )
                return {"state": "parsed"}
            else:
                # Decoding failed, store raw data
                self.write({"content": ""})  # Clear content
                self._http_store_content(
                    content, content_type, filename, retrieval_details, record
                )  # Store raw
                self._post_styled_message(
                    f"Failed to decode text content from URL: {final_url}. Storing raw data.",
                    "warning",
                )
                return {"state": "parsed"}
        else:
            target_fields = retrieval_details["target_fields"]
            target_field_type = None
            content_key = None
            target_field_type = record._fields[target_fields["content"]].type
            content_key = target_fields["content"]
            if content_key and target_field_type == "binary":
                self._http_store_content(
                    content, content_type, filename, retrieval_details, record
                )
                self._post_styled_message(
                    f"Successfully retrieved binary content from URL: {final_url} (original: {initial_url})",
                    "success",
                )
            else:
                raise UserError(
                    _(
                        "Can not store binary data in field %s for model %s from URL: %s (original: %s)"
                    )
                    % (content_key, record._name, final_url, initial_url)
                )

            return {"state": "retrieved"}
