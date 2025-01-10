import unittest
from unittest.mock import patch
from fileai.api import GeminiAPI

class TestGeminiAPI(unittest.TestCase):

    @patch('google.genai.Client')
    def test_generate_content(self, mock_client):
        mock_model = mock_client.return_value
        mock_response = mock_model.models.generate_content.return_value
        mock_response.text = '{"key": "value"}'

        api = GeminiAPI()
        response = api.process_content_with_llm("test prompt")
        self.assertEqual(response, {"key": "value"})

    @patch('fileai.api.GeminiAPI._upload_content')
    @patch('fileai.api.ContentAdapter.adapt_content')
    def test_prepare_contents(self, mock_adapt_content, mock_upload_content):
        mock_adapt_content.return_value = (None, [])
        mock_upload_content.return_value = "mocked upload content"

        api = GeminiAPI()
        contents, _ = api._prepare_contents("test prompt", "test content")
        self.assertEqual(len(contents), 2)
        self.assertEqual(contents[0].parts[0].text, "test content")
        self.assertEqual(contents[1].parts[0].text, "test prompt")

    @patch('fileai.api.GeminiAPI._upload_content')
    @patch("fileai.api.ContentAdapter.adapt_content")
    def test_prepare_contents_with_assets(self, mock_adapt_content, mock_upload_content):
        mock_adapt_content.side_effect = lambda asset: (asset, ["temp_file_path"])
        mock_upload_content.return_value = "mocked upload content"

        class MockAsset:
            def __init__(self, temp_path, mime_type):
                self.temp_path = temp_path
                self.mime_type = mime_type

        image_asset = MockAsset("image.jpg", "image/jpeg")
        pdf_asset = MockAsset("document.pdf", "application/pdf")

        api = GeminiAPI()
        contents, _ = api._prepare_contents("test prompt", asset=image_asset)
        self.assertEqual(len(contents), 2)
        contents, _ = api._prepare_contents("test prompt", asset=pdf_asset)
        self.assertEqual(len(contents), 2)

if __name__ == '__main__':
    unittest.main()
