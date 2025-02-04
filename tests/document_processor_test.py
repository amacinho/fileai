import unittest
import tempfile
from unittest.mock import Mock, patch, mock_open, call
import sys
import os # Import os module
from pathlib import Path

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fileai.document_processor import DocumentProcessor
from fileai.document_handlers import get_handler, BaseDocumentHandler
from fileai.filesystem_manager import FileSystemManager
from fileai.directory_manager import DirectoryManager
from fileai.document_categorizer import DocumentCategorizer
from fileai.api import GeminiAPI
from fileai.config import Asset


class TestDocumentProcessor(unittest.TestCase):
    def setUp(self):
        self.mock_api = Mock(spec=GeminiAPI)
        self.input_dir = tempfile.TemporaryDirectory()
        self.output_dir = tempfile.TemporaryDirectory()
        self.input_path = Path(self.input_dir.name)
        self.output_path = Path(self.output_dir.name)
        self.processor = DocumentProcessor(self.input_path, self.output_path, self.mock_api)

        # Mock the component classes
        self.processor.fs_manager = Mock(spec=FileSystemManager)
        self.processor.dir_manager = Mock(spec=DirectoryManager)
        self.processor.categorizer = Mock(spec=DocumentCategorizer)

        # Copy fixture files to temporary input directory
        os.system(f"cp tests/fixtures/input/* {self.input_path}")

        # List files in temporary input directory to verify copy
        print(f"Files in temp input dir: {os.listdir(self.input_path)}")


    def tearDown(self):
        self.input_dir.cleanup()
        self.output_dir.cleanup()

    def test_validate_document(self):
        # Test supported extensions
        with patch('fileai.document_handlers.get_handler') as mock_get_handler:
            mock_get_handler.return_value = Mock(spec=BaseDocumentHandler)
            self.assertTrue(self.processor._validate_document(Path("test.pdf")))
            self.assertTrue(self.processor._validate_document(Path("test.jpg")))
            self.assertTrue(self.processor._validate_document(Path("test.txt")))

            # Test unsupported extensions
            mock_get_handler.return_value = None
            self.assertFalse(self.processor._validate_document(Path("test.exe")))
            self.assertFalse(self.processor._validate_document(Path("test.zip")))

            # Test .DS_Store
            self.assertFalse(self.processor._validate_document(Path(".DS_Store")))

    def test_extract_content(self):
        mock_handler = Mock(spec=BaseDocumentHandler)
        mock_handler.process.return_value = ("test content", Asset(file_type="test_type"))
        mock_handler.file_type = "test_type"

        with patch('fileai.document_handlers.get_handler', return_value=mock_handler):
            content, asset = self.processor._extract_content(Path("test.txt"))
            self.assertEqual(content, "test content")
            self.assertEqual(asset.type, "test_type")

        # Test unsupported file
        with patch('fileai.document_handlers.get_handler', return_value=None):
            content, asset = self.processor._extract_content(Path("test.unknown"))
            self.assertIsNone(content)
            self.assertIsNone(asset)

    def test_process_document(self):
        test_file = Path("/test/input/document.pdf")
        
        # Mock handler and content extraction
        mock_handler = Mock(spec=BaseDocumentHandler)
        mock_handler.process.return_value = ("test content", Asset(file_type="document"))
        mock_handler.file_type = "document"
        
        with patch('fileai.document_handlers.get_handler', return_value=mock_handler):
            # Mock categorizer response
            self.processor.categorizer.categorize_document.return_value = ("new_name", "category")
            
            # Mock directory manager
            self.processor.dir_manager.get_category_path.return_value = self.output_path / "category"
            
            # Mock filesystem operations
            self.processor.fs_manager.is_same_file.return_value = False
            self.processor.fs_manager.ensure_unique_path.return_value = self.output_path / "category" / "new_name.pdf"
            
            # Test successful processing
            result = self.processor.process_document(test_file)
            
            # Verify the workflow
            self.processor.categorizer.categorize_document.assert_called_once()
            self.processor.dir_manager.get_category_path.assert_called_once_with("category")
            self.processor.fs_manager.move_file.assert_called_once_with(test_file, self.output_path / "category" / "new_name.pdf")
            self.processor.dir_manager.cleanup_empty_dirs.assert_called_once()
            
            self.assertIsNotNone(result)

    def test_duplicate_handling(self):
        test_file = Path("/test/input/document.pdf")
        
        # Mock handler and content extraction
        mock_handler = Mock(spec=BaseDocumentHandler)
        mock_handler.process.return_value = ("test content", Asset(file_type="document"))
        mock_handler.file_type = "document"
        
        with patch('fileai.document_handlers.get_handler', return_value=mock_handler):
            # Mock categorizer response
            self.processor.categorizer.categorize_document.return_value = ("new_name", "category")
            
            # Mock directory manager
            self.processor.dir_manager.get_category_path.return_value = self.output_path / "category"
            
            # Test duplicate file scenario
            self.processor.fs_manager.is_same_file.return_value = True
            
            result = self.processor.process_document(test_file)
            
            # Verify duplicate handling
            self.processor.fs_manager.remove_file.assert_called_once_with(test_file)
            self.assertIsNone(result)

    def test_process_directory(self):
        # Mock file discovery
        mock_files = [
            Path("/test/input/file1.txt"),
            Path("/test/input/file2.pdf"),
            Path("/test/input/file3.jpg"),
        ]
        
        with patch('pathlib.Path.rglob') as mock_rglob:
            mock_rglob.return_value = mock_files
            
            # Mock is_file and is_relative_to checks
            with patch('pathlib.Path.is_file', return_value=True):
                with patch('pathlib.Path.is_relative_to', return_value=False):
                    with patch.object(DocumentProcessor, 'process_document') as mock_process:
                        self.processor.process_directory()
                        
                        # Verify all files were processed
                        self.assertEqual(mock_process.call_count, len(mock_files))
                        mock_process.assert_has_calls([call(file) for file in mock_files])


if __name__ == "__main__":
    unittest.main()
