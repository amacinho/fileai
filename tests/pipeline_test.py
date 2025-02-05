import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import shutil

from fileai.document_categorizer import DocumentCategorizer
from fileai.file_operator import FileOperator
from fileai.pipeline import DocumentPipeline

class TestDocumentPipeline(unittest.TestCase):
    def setUp(self):
        # Create temporary directories for input and output files
        self.input_dir = tempfile.TemporaryDirectory()
        self.output_dir = tempfile.TemporaryDirectory()
        self.input_path = Path(self.input_dir.name)
        self.output_path = Path(self.output_dir.name)

        fixture_input = Path("tests/fixtures/input")
        shutil.copytree(fixture_input, self.input_path, dirs_exist_ok=True)

        # Set up mock API
        self.api_mock = Mock()
        self.api_mock.get_response.return_value = {
            "doc_owner": "test owner",
            "doc_topic": "test document",
            "doc_date": "2025-02-04",
            "doc_folder": "work",
        }

    def tearDown(self):
        self.input_dir.cleanup()
        self.output_dir.cleanup()

    def test_pipeline_single_file(self):
        categorizer = DocumentCategorizer(self.api_mock)
        file_operator = FileOperator(input_base_path=self.input_path, output_base_path=self.output_path, remove_input_files=True)
        pipeline = DocumentPipeline(categorizer=categorizer, file_operator=file_operator)
        supported_extensions = {'.doc', '.docx', '.html', '.pdf', '.txt', '.rtf'}
        for file in self.input_path.iterdir():
            if file.suffix not in supported_extensions:
                print(f"\nSkipping unsupported file type: {file.suffix}")
                continue
            try:
                target_path = pipeline.process(file)
                # Assert the expected output file exists in the right place
                expected_output_path = (
                    self.output_path
                    / "work"
                    / f"2025-02-04-test-document-test-owner{file.suffix}"
                )
                print(f"\nExpected path: {expected_output_path}")
                print(f"Actual path: {target_path}")
                print("Output directory contents:")
                for p in self.output_path.rglob("*"):
                    print(f"  {p.relative_to(self.output_path)}")
                self.assertEqual(target_path, expected_output_path)
            except ValueError as e:
                if "Unsupported file type" in str(e):
                    print(f"\nSkipping unsupported file type: {file.suffix}")
                    continue
                raise
    
if __name__ == '__main__':
    unittest.main()
