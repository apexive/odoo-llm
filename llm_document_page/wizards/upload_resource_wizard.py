import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class UploadResourceWizardInherit(models.TransientModel):
    _inherit = "llm.upload.resource.wizard"

    download_as_document_page = fields.Boolean(
        string="Download URLs as Document Pages",
        default=False,
        help="If checked, external URLs will be downloaded and stored as 'document.page' records instead of 'ir.attachment'.",
    )

    def _process_external_urls(self, collection, attachment_model_id, file_count):
        """Override: Process external URLs, creating document.page if requested."""
        self.ensure_one()

        # If checkbox is not ticked, use the original ir.attachment logic
        if not self.download_as_document_page:
            return super()._process_external_urls(
                collection, attachment_model_id, file_count
            )

        # Checkbox is ticked: Process URLs to create document.page records
        created_resources = self.env["llm.resource"]
        IrModel = self.env["ir.model"]

        # Get document.page model ID
        document_page_model_id_rec = IrModel.search(
            [("model", "=", "document.page")], limit=1
        )
        if not document_page_model_id_rec:
            _logger.warning(
                "document.page model not found. Falling back to ir.attachment creation."
            )
            # Fallback to original method if model is missing
            return super()._process_external_urls(
                collection, attachment_model_id, file_count
            )
        document_page_model_id = document_page_model_id_rec.id

        if not self.external_urls:
            return created_resources

        urls = [url.strip() for url in self.external_urls.split("\n") if url.strip()]

        for index, url in enumerate(urls):
            # Use inherited _extract_filename_from_url
            filename = self._extract_filename_from_url(url)
            resource_name = self.resource_name_template.format(
                filename=filename,
                collection=collection.name or "default",
                index=file_count + index + 1,
            )

            # Create document.page
            try:
                doc_page = self.env["document.page"].create(
                    {
                        "name": resource_name,  # Use resource name for consistency
                        "source_url": url,
                        # Content will be filled by retriever
                    }
                )
            except Exception as e:
                _logger.error(
                    f"Failed to create document.page for URL {url}: {e}", exc_info=True
                )
                continue  # Skip this URL

            # Create llm.resource linking to the document.page
            try:
                resource = self.env["llm.resource"].create(
                    {
                        "name": resource_name,
                        "model_id": document_page_model_id,
                        "res_id": doc_page.id,
                        "collection_ids": [(4, collection.id)],
                        "retriever": "http",  # Assuming http retriever handles doc page
                    }
                )
                created_resources |= resource
            except Exception as e:
                _logger.error(
                    f"Failed to create llm.resource for URL {url} (doc_page: {doc_page.id}): {e}",
                    exc_info=True,
                )
                # Clean up orphan document.page record
                doc_page.exists().unlink()

        return created_resources
