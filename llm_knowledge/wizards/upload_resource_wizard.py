import logging
import os
import re
from urllib.parse import urlparse

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class UploadResourceWizard(models.TransientModel):
    _name = "llm.upload.resource.wizard"  # Keep original name or rename if preferred
    _description = "Upload RAG Resources Wizard"

    collection_id = fields.Many2one(
        "llm.knowledge.collection",  # Target llm.knowledge.collection
        string="Collection",
        required=True,  # Collection is required here
        help="Collection to which resources will be added",
    )
    file_ids = fields.Many2many(
        "ir.attachment", string="Files", help="Local files to upload"
    )
    external_urls = fields.Text(
        string="External URLs", help="External URLs to include, one per line"
    )
    # Field renamed for clarity
    resource_name_template = fields.Char(
        string="Resource Name Template",
        default="{filename}",
        help="Template for resource names. Use {filename}, {collection}, and {index} as placeholders.",
        required=True,
    )
    process_immediately = fields.Boolean(
        string="Process Immediately",
        default=False,
        help="If checked, resources will be immediately processed through the RAG pipeline",
    )
    state = fields.Selection(
        [
            ("confirm", "Confirm"),
            ("done", "Done"),
        ],
        default="confirm",
    )
    # Field renamed and target model changed
    created_resource_ids = fields.Many2many(
        "llm.resource",  # Target llm.resource
        string="Created Resources",
    )
    created_count = fields.Integer(string="Created", compute="_compute_created_count")

    @api.depends("created_resource_ids")
    def _compute_created_count(self):
        for wizard in self:
            wizard.created_count = len(wizard.created_resource_ids)

    def _extract_filename_from_url(self, url):
        """Extract a filename from a URL, handling query parameters.

        Args:
            url (str): The URL to extract the filename from.

        Returns:
            str: The extracted filename or a default name if extraction fails.
        """
        parsed_url = urlparse(url)
        # Get the last part of the path
        filename = (
            os.path.basename(parsed_url.path)
            if parsed_url.path
            else "resource_from_url"
        )
        # Remove potential query parameters or fragments if they got stuck
        filename = re.sub(r"[?#].*", "", filename)
        # Basic sanitization (replace common problematic chars)
        filename = re.sub(r'[\\/:*?"<>|]', "_", filename)
        # Limit length
        return filename[:100] or "resource_from_url"  # Ensure not empty

    # ----------------------------------------------------
    # Private Helper Methods for Processing
    # ----------------------------------------------------
    def _process_file_uploads(self, collection, attachment_model_id):
        """Process uploaded files (file_ids)."""
        self.ensure_one()
        created_resources = self.env["llm.resource"]
        if not self.file_ids:
            return created_resources

        for index, attachment in enumerate(self.file_ids):
            resource_name = self.resource_name_template.format(
                filename=attachment.name or f"file_{index + 1}",
                collection=collection.name,
                index=index + 1,
            )

            # Create RAG resource linking to the attachment
            resource = self.env["llm.resource"].create(
                {
                    "name": resource_name,
                    "model_id": attachment_model_id,
                    "res_id": attachment.id,
                    "collection_ids": [(4, collection.id)],
                    # Implicitly uses default retriever for ir.attachment
                }
            )
            created_resources |= resource
        return created_resources

    def _process_external_urls(self, collection, attachment_model_id, file_count):
        """Process external URLs."""
        self.ensure_one()
        created_resources = self.env["llm.resource"]
        if not self.external_urls:
            return created_resources

        urls = [url.strip() for url in self.external_urls.split("\n") if url.strip()]
        for index, url in enumerate(urls):
            # Extract filename from URL for naming
            filename = self._extract_filename_from_url(url)

            resource_name = self.resource_name_template.format(
                filename=filename,
                collection=collection.name,
                index=file_count + index + 1,  # Continue index from files
            )

            # Create attachment for URL
            try:
                attachment = self.env["ir.attachment"].create(
                    {
                        "name": filename,
                        "type": "url",
                        "url": url,
                    }
                )
            except Exception as e:
                _logger.error(
                    f"Failed to create attachment for URL {url}: {e}", exc_info=True
                )
                continue  # Skip this URL

            # Create RAG resource using model_id
            try:
                resource = self.env["llm.resource"].create(
                    {
                        "name": resource_name,
                        "model_id": attachment_model_id,
                        "res_id": attachment.id,
                        "collection_ids": [(4, collection.id)],
                        "retriever": "http",
                    }
                )
                created_resources |= resource
            except Exception as e:
                _logger.error(
                    f"Failed to create llm.resource for URL {url} (attachment: {attachment.id}): {e}",
                    exc_info=True,
                )
                # Optionally delete the created attachment if resource fails
                # attachment.exists().unlink()

        return created_resources

    # ----------------------------------------------------
    # Main Action
    # ----------------------------------------------------
    def action_upload_resources(self):
        """Create RAG resources from files or URLs and process them.

        This method handles both direct file uploads and external URLs,
        creating corresponding llm.resource records linked to ir.attachment.
        It then optionally triggers the processing pipeline immediately.
        """
        self.ensure_one()
        collection = self.collection_id
        IrModel = self.env["ir.model"]

        if not self.file_ids and not self.external_urls:
            raise UserError(_("Please provide at least one file or URL"))

        # Get ir.attachment model ID (needed for both files and default URL handling)
        attachment_model_id_rec = IrModel.search(
            [("model", "=", "ir.attachment")], limit=1
        )
        if not attachment_model_id_rec:
            raise UserError(_("Could not find ir.attachment model"))
        attachment_model_id = attachment_model_id_rec.id

        # Process Files
        file_resources = self._process_file_uploads(collection, attachment_model_id)

        # Process URLs
        url_resources = self._process_external_urls(
            collection, attachment_model_id, len(self.file_ids)
        )

        # Combine results
        created_resources = file_resources | url_resources

        # Process resources if requested (full RAG pipeline)
        if self.process_immediately and created_resources:
            _logger.info(f"Processing {len(created_resources)} resources immediately.")
            for resource in created_resources:
                try:
                    resource.process_resource()  # Calls retriever, parser, embedder
                except Exception as e:
                    _logger.error(
                        f"Error processing resource {resource.id} ({resource.name}): {e}",
                        exc_info=True,
                    )
                    resource._post_styled_message(
                        f"Processing failed: {str(e)}", "error"
                    )

        # Update wizard state
        self.write(
            {
                "state": "done",
                "created_resource_ids": [(6, 0, created_resources.ids)],
            }
        )

        # Return action to show results or stay in wizard
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "context": self.env.context,
        }

    # Method renamed for clarity
    def action_view_resources(self):
        """Open the created resources"""
        return {
            "name": "Uploaded RAG Resources",
            "type": "ir.actions.act_window",
            "res_model": "llm.resource",  # Target llm.resource
            "view_mode": "list,form,kanban",
            "domain": [
                ("id", "in", self.created_resource_ids.ids)
            ],  # Use renamed field
            # Use the specific views defined in llm_knowledge for llm.resource
            "view_ids": [
                (5, 0, 0),
                (
                    0,
                    0,
                    {
                        "view_mode": "kanban",
                        "view_id": self.env.ref(
                            "llm_knowledge.view_llm_resource_kanban"
                        ).id,
                    },
                ),
                (
                    0,
                    0,
                    {
                        "view_mode": "list",
                        "view_id": self.env.ref(
                            "llm_knowledge.view_llm_resource_tree"
                        ).id,
                    },
                ),
                (
                    0,
                    0,
                    {
                        "view_mode": "form",
                        "view_id": self.env.ref(
                            "llm_knowledge.view_llm_resource_form"
                        ).id,
                    },
                ),
            ],
            "search_view_id": [
                self.env.ref("llm_knowledge.view_llm_resource_search").id
            ],
        }
