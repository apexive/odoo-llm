from odoo.tests.common import TransactionCase


class _FakeFileOutput:
    def __init__(self, url):
        self.url = url

    def __iter__(self):
        return iter([b"a", b"b", b"c"])


class TestReplicateGenerationOutputs(TransactionCase):
    def setUp(self):
        super().setUp()
        self.provider = self.env["llm.provider"].create(
            {
                "name": "Test Replicate Provider",
                "service": "replicate",
            }
        )

    def test_prepare_result_preserves_single_file_output(self):
        result = _FakeFileOutput("https://replicate.delivery/output.mp3")

        prepared = self.provider._replicate_prepare_result_for_extraction(result)

        self.assertIs(prepared, result)

    def test_extract_single_url_detects_audio_content_type(self):
        url_data = self.provider._replicate_extract_single_url_with_metadata(
            _FakeFileOutput("https://replicate.delivery/output.mp3")
        )

        self.assertEqual(url_data["url"], "https://replicate.delivery/output.mp3")
        self.assertEqual(url_data["filename"], "output.mp3")
        self.assertEqual(url_data["content_type"], "audio/mpeg")
