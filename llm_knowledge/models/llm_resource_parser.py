import base64
import json
import logging

from markdownify import markdownify as md

try:
    import pymupdf
except ImportError:
    pymupdf = None

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class LLMResourceParser(models.Model):
    _inherit = "llm.resource"

    parser = fields.Selection(
        selection="_get_available_parsers",
        string="Parser",
        default="default",
        required=True,
        help="Method used to parse resource content",
        tracking=True,
    )

    @api.model
    def _get_available_parsers(self):
        """Get all available parser methods"""
        return [
            ("default", "Default Parser"),
            ("json", "JSON Parser"),
        ]

    def parse(self):
        """Parse the retrieved content to markdown"""
        # Lock resources and process only the successfully locked ones
        resources = self._lock(state_filter="retrieved")
        if not resources:
            return False

        for resource in resources:
            try:
                # Get the related record
                record = self.env[resource.res_model].browse(resource.res_id)
                if not record.exists():
                    raise UserError(_("Referenced record not found"))

                # If the record has a specific rag_parse method, call it
                if hasattr(record, "llm_get_fields"):
                    fields = record.llm_get_fields(record)
                else:
                    # Call get_fields on the individual resource to ensure singleton
                    fields = resource.get_fields(record)

                for field in fields:
                    # TODO: Should it be self._parse_field?
                    success = resource._parse_field(record, field)

                if success:
                    resource.write({"state": "parsed"})
                    self.env.cr.commit()
                    resource._post_styled_message(
                        "Resource successfully parsed", "success"
                    )
                else:
                    resource._post_styled_message(
                        "Parsing completed but did not return success", "warning"
                    )

            except Exception as e:
                _logger.error(
                    "Error parsing resource %s: %s",
                    resource.id,
                    str(e),
                    exc_info=True,
                )
                resource._post_styled_message(
                    f"Error parsing resource: {str(e)}", "error"
                )
                if resource.collection_ids:
                    resource.collection_ids._post_styled_message(
                        f"Error parsing resource: {str(e)}", "error"
                    )
            finally:
                resource._unlock()
        resources._unlock()

    def _get_parser(self, record, field_name, mimetype):
        if self.parser != "default":
            return getattr(self, f"parse_{self.parser}")
        record_name = (
            record.display_name
            if hasattr(record, "display_name")
            else f"{record._name} #{record.id}"
        )

        is_markdown = ".md" in record_name.lower()
        if mimetype == "application/pdf":
            return self._parse_pdf
        # special case, as odoo detects markdowns as application/octet-stream
        elif mimetype == "application/octet-stream" and is_markdown:
            return self._parse_text
        elif "html" in mimetype:
            return self._parse_html
        elif mimetype.startswith("text/"):
            return self._parse_text
        elif mimetype.startswith("image/"):
            # For images, store a reference in the content
            return self._parse_image
        elif mimetype == "application/json":
            return self.parse_json
        else:
            return self._parse_default

    def _parse_field(self, record, field):
        self.ensure_one()
        parser_method = self._get_parser(record, field["field_name"], field["mimetype"])
        return parser_method(record, field)

    def get_fields(self, record):
        """
        Default parser implementation - generates a generic markdown representation
        based on commonly available fields

        :returns
        [{"field_name": field_name, "mimetype": mimetype, "rawcontent": rawcontent}]
        """
        self.ensure_one()

        results = []

        # Start with the record name/display_name if available
        record_name_field = (
            "display_name" if hasattr(record, "display_name") else "name"
        )
        record_name = (
            record[record_name_field]
            if hasattr(record, record_name_field)
            else f"{record._name} #{record.id}"
        )
        if record_name:
            results.append(
                {
                    "field_name": record_name_field,
                    "mimetype": "text/plain",
                    "rawcontent": record_name,
                }
            )

        # Try to include description or common text fields
        common_text_fields = [
            "description",
            "note",
            "comment",
            "message",
            "content",
            "body",
            "text",
        ]
        for field_name in common_text_fields:
            if hasattr(record, field_name) and record[field_name]:
                # Use text/plain for now, could be refined based on field type
                results.append(
                    {
                        "field_name": field_name,
                        "mimetype": "text/plain",
                        "rawcontent": record[field_name],
                    }
                )

        return results

    def parse_json(self, record, field):
        """
        JSON parser implementation - converts record data to JSON and then to markdown
        """
        self.ensure_one()

        # Get record name or default to model name and ID
        record_name = (
            record.display_name
            if hasattr(record, "display_name")
            else f"{record._name} #{record.id}"
        )

        # Create a dictionary with record data
        record_data = {}
        for field_name, field in record._fields.items():
            try:
                # Skip binary fields and internal fields
                if field.type == "binary" or field_name.startswith("_"):
                    continue

                # Handle many2one fields
                if field.type == "many2one" and record[field_name]:
                    record_data[field_name] = {
                        "id": record[field_name].id,
                        "name": record[field_name].display_name,
                    }
                # Handle many2many and one2many fields
                elif field.type in ["many2many", "one2many"]:
                    record_data[field_name] = [
                        {"id": r.id, "name": r.display_name} for r in record[field_name]
                    ]
                # Handle other fields
                else:
                    record_data[field_name] = record[field_name]
            except Exception as e:
                _logger.error(f"Skipping field {field_name}: {str(e)}")
                self._post_styled_message(
                    f"Skipping field {field_name}: {str(e)}", "warning"
                )
                continue
        # Format as markdown
        content = [f"# {record_name}"]
        content.append("\n## JSON Data\n")
        content.append("```json")
        content.append(json.dumps(record_data, indent=2, default=str))
        content.append("```")

        # Update resource content
        self.content = "\n".join(content)

        return True

    def _parse_pdf(self, record, field):
        """Parse PDF file and extract text and images"""
        # Decode attachment data

        if field["mimetype"] != "application/pdf":
            return False

        # Open PDF using PyMuPDF
        text_content = []
        image_count = 0
        page_count = 0
        # no need to decode as passing raw data should work here
        pdf_data = field["rawcontent"]

        # Create a BytesIO object from the PDF data
        with pymupdf.open(stream=pdf_data, filetype="pdf") as doc:
            # Store page count before document is closed
            page_count = doc.page_count

            # Process each page
            for page_num in range(page_count):
                page = doc[page_num]

                # Extract text
                text = page.get_text()
                text_content.append(f"## Page {page_num + 1}\n\n{text}")

                # Extract images
                image_list = page.get_images(full=True)
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    try:
                        base_image = doc.extract_image(xref)
                        if base_image:
                            # Store image as attachment
                            image_data = base_image["image"]
                            image_ext = base_image["ext"]
                            image_name = f"image_{page_num}_{img_index}.{image_ext}"

                            # Create attachment for the image
                            img_attachment = record.env["ir.attachment"].create(
                                {
                                    "name": image_name,
                                    "datas": base64.b64encode(image_data),
                                    "res_model": "llm.resource",
                                    "res_id": self.id,
                                    "mimetype": f"image/{image_ext}",
                                }
                            )

                            # Add image reference to markdown content
                            if img_attachment:
                                image_url = f"/web/image/{img_attachment.id}"
                                text_content.append(f"\n![{image_name}]({image_url})\n")
                                image_count += 1
                    except Exception as e:
                        self._post_styled_message(
                            f"Error extracting image: {str(e)}", "warning"
                        )

        # Join all content
        final_content = "\n\n".join(text_content)

        # Update resource with extracted content
        self.content = final_content

        return True

    def _parse_text(self, _, field):
        self.content = field["rawcontent"]
        return True

    def _parse_html(self, _, field):
        self.content = md(field["rawcontent"])
        return True

    def _parse_image(self, record, _):
        image_url = f"/web/image/{record.id}"
        self.content = f"![{record.name}]({image_url})"
        return True

    def _parse_default(self, record, field):
        # Default to a generic description for unsupported types
        mimetype = field["mimetype"]
        self.content = f"""
            # {record.name}

            **File Type**: {mimetype}
            **Description**: This file is of type {mimetype} which cannot be directly parsed into text content.
            **Access**: [Open file](/web/content/{record.id})
                            """
        return True
