"""Tests for website media management tools"""

import base64

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestMediaTools(TransactionCase):
    """Test media find, upload, info, delete tools"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_tools = cls.env["website.tool.media"]
        cls.website = cls.env["website"].search([], limit=1)
        if not cls.website:
            raise Exception("No website found for testing")

        # Create a test attachment
        cls.test_attachment = cls.env["ir.attachment"].create(
            {
                "name": "llm_test_image.png",
                "type": "binary",
                "datas": base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100),
                "mimetype": "image/png",
                "public": True,
                "res_model": "ir.ui.view",
                "website_id": cls.website.id,
            }
        )

    def test_find_media(self):
        """Test finding media files"""
        result = self.media_tools.website_find_media(name="llm_test_image")
        self.assertGreaterEqual(result["count"], 1)
        names = [m["name"] for m in result["media"]]
        self.assertIn("llm_test_image.png", names)

    def test_find_media_by_type(self):
        """Test finding media by media_type shortcut"""
        result = self.media_tools.website_find_media(media_type="image")
        self.assertIsInstance(result["media"], list)

    def test_find_media_by_mimetype(self):
        """Test finding media by exact mimetype"""
        result = self.media_tools.website_find_media(mimetype="image/png")
        self.assertIsInstance(result["media"], list)

    def test_find_media_result_fields(self):
        """Test that find results have all expected fields"""
        result = self.media_tools.website_find_media(name="llm_test_image")
        self.assertGreater(result["count"], 0)
        media = result["media"][0]
        for field in ["id", "name", "mimetype", "url", "file_size", "create_date"]:
            self.assertIn(field, media)

    def test_upload_image_base64(self):
        """Test uploading an image from base64 data"""
        data = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50).decode()
        result = self.media_tools.website_upload_image_base64(
            data=data,
            name="uploaded_test.png",
            mimetype="image/png",
        )
        self.assertIn("id", result)
        self.assertEqual(result["name"], "uploaded_test.png")
        self.assertEqual(result["mimetype"], "image/png")
        self.assertIn("image_url", result)

    def test_upload_image_base64_invalid_mimetype(self):
        """Test that invalid mimetype is rejected"""
        data = base64.b64encode(b"test").decode()
        with self.assertRaises(UserError):
            self.media_tools.website_upload_image_base64(
                data=data,
                name="bad.txt",
                mimetype="text/plain",
            )

    def test_get_media_info(self):
        """Test getting media info by ID"""
        result = self.media_tools.website_get_media_info(
            attachment_id=self.test_attachment.id
        )
        self.assertEqual(result["id"], self.test_attachment.id)
        self.assertEqual(result["name"], "llm_test_image.png")
        self.assertEqual(result["mimetype"], "image/png")
        self.assertIn("url", result)
        self.assertIn("checksum", result)

    def test_get_media_info_not_found(self):
        """Test that non-existent attachment raises error"""
        with self.assertRaises(UserError):
            self.media_tools.website_get_media_info(attachment_id=999999999)

    def test_delete_media(self):
        """Test deleting a media attachment"""
        att = self.env["ir.attachment"].create(
            {
                "name": "to_delete.png",
                "type": "binary",
                "datas": base64.b64encode(b"\x89PNG\r\n\x1a\n"),
                "mimetype": "image/png",
                "public": True,
                "website_id": self.website.id,
            }
        )
        result = self.media_tools.website_delete_media(attachment_id=att.id)
        self.assertIn("message", result)
        self.assertFalse(att.exists())
