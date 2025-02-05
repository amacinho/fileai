import unittest
from unittest.mock import patch
from fileai.api import GeminiAPI

class TestGeminiAPI(unittest.TestCase):
    @patch('google.genai.Client')
    def test_prepare_contents(self, mock_client):
        mock_file_upload_result = unittest.mock.Mock()
        mock_file_upload_result.uri = "mock_uri"
        mock_client.return_value.files.upload.return_value = mock_file_upload_result


        api = GeminiAPI()
        contents = api._prepare_contents(
            "test prompt", path="apath.pdf")

        self.assertEqual(len(contents), 2)
        upload_content = contents[0]
        prompt_content = contents[1]

        self.assertEqual(upload_content.role, "user")
        self.assertEqual(len(upload_content.parts), 1)
        self.assertEqual(upload_content.parts[0].file_data.file_uri, "mock_uri")
        self.assertEqual(upload_content.parts[0].file_data.mime_type, 'application/pdf')

        self.assertEqual(prompt_content.role, "user")
        self.assertEqual(prompt_content.parts[0].text, "test prompt")


if __name__ == '__main__':
    unittest.main()
