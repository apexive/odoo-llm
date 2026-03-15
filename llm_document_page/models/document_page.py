from markdownify import markdownify as md

from odoo import fields, models


class DocumentPage(models.Model):
    """Extend document.page to add integration with LLM RAG module."""

    _inherit = "document.page"

    # == Fields added for LLM Integration ==
    source_url = fields.Char(
        string="Source URL",
        readonly=True,
        index=True,
        copy=False,
        help="The original URL from which this page content was retrieved, if applicable.",
    )

    def llm_get_retrieval_details(self):
        """Provides details needed by llm.resource to retrieve content.
        Returns:
            Dictionary containing details about how to retrieve content
            The dictionary should contain the following elements:
                type: str - type of retrieval, either "url" or "binary"
                field: str - name of the field to retrieve the content from
                target_fields: dictionary containing details about how to store the content
                    The dictionary should contain the following elements:
                        content(required): str - name of the field to store the content in
                        mimetype: str - mimetype of the content
                        filename: str - name of the field to store the filename in
                        type: str - type of the field to store the type in
        """
        self.ensure_one()
        if self.source_url:
            return {
                "type": "url",
                "field": "source_url",
                "target_fields": {
                    "content": "content",
                },
            }
        else:
            return None

    def llm_get_fields(self, _):
        """
        Parse document.page content for RAG.
        This method is called by the LLM RAG module during document processing.

        :param llm_resource: The llm.resource record being processed
        :return: Boolean indicating success
        """
        self.ensure_one()

        # Start with the page content
        content_parts = [md(self.content)]

        # If there are child pages, include their titles as references
        if self.child_ids:
            content_parts.append("\n## Related Pages\n")
            for child in self.child_ids:
                content_parts.append(f"- [{child.name}]({child.backend_url})")

        return [
            {
                "field_name": "content",
                "mimetype": "text/markdown",
                "rawcontent": "\n\n".join(content_parts),
            }
        ]
