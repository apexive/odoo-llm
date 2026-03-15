from odoo import models


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def llm_get_fields(self, _):
        self.ensure_one()
        is_markdown = (
            self.name.lower().endswith(".md") and self.mimetype == "stream/octet-stream"
        )
        # TODO: optimize this later for not loading raw data in memory
        return [
            {
                "field_name": "datas",
                "mimetype": "text/markdown" if is_markdown else self.mimetype,
                "rawcontent": self.raw,
            }
        ]

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
        data_type = "url" if self.type == "url" else "binary"
        details = {
            "type": data_type,
            "field": "datas" if data_type == "binary" else "url",
            "target_fields": {
                "content": "datas",
                "mimetype": "mimetype",
                "filename": "name",
                "type": "type",
            },
        }
        return details
