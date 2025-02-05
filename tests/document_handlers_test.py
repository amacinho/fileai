import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from PIL import Image
import os # Import os module

from fileai.document_handlers import (
    get_handler,
    BaseDocumentHandler,
    ImageHandler,
    DocHandler,
    XlsxHandler,
    PdfHandler,
    TextHandler
)

@pytest.fixture
def test_files_dir(tmp_path):
    """Create a temporary directory with test files."""
    # Create test files
    files_dir = tmp_path / "test_files"
    files_dir.mkdir()
    
    # Copy fixture files to temporary test directory (verbose output)
    os.system(f"cp -v tests/fixtures/input/* {files_dir}")
    
    return files_dir

def test_base_handler():
    """Test BaseDocumentHandler abstract class."""
    class TestHandler(BaseDocumentHandler):
        supported_extensions = ['.test']
    
    # Should raise NotImplementedError if process is not implemented
    with pytest.raises(NotImplementedError):
        TestHandler.process(Path("test.file"))
    
    # Test extension checking
    assert TestHandler.supported_extension('.test')
    assert not TestHandler.supported_extension('.wrong')

def test_get_handler():
    """Test handler factory function."""
    # Test valid extensions
    assert get_handler('.jpg') == ImageHandler
    assert get_handler('.docx') == DocHandler
    assert get_handler('.xlsx') == XlsxHandler
    assert get_handler('.pdf') == PdfHandler
    assert get_handler('.txt') == TextHandler
    
    # Verify .doc is not supported
    assert get_handler('.doc') is None
    
    # Test case insensitivity
    assert get_handler('.JPG') == ImageHandler
    assert get_handler('.PDF') == PdfHandler
    
    # Test unsupported extension
    assert get_handler('.unsupported') is None

def test_text_handler(test_files_dir):
    """Test TextHandler functionality, allowing actual temp file creation."""
    text_file = test_files_dir / "test.txt"
    expected_content = """Shopping list  2025 February 02

Apples
Oranges
Butter"""

    # Test successful processing - no mocking of file operations
    temp_path = TextHandler.process(text_file)

    # Verify temp path
    assert temp_path is not None
    assert isinstance(temp_path, Path)
    assert temp_path.exists()

    # Verify temp file content
    actual_content = temp_path.read_text()
    assert actual_content == expected_content

    # Cleanup temp file
    temp_path.unlink()

    # Test error handling with non-existent file
    with pytest.raises(Exception):
        TextHandler.process(test_files_dir / "nonexistent.txt")


def test_image_handler(test_files_dir):
    """Test ImageHandler functionality."""
    print(f"Files in test_image_handler temp dir: {os.listdir(test_files_dir)}") # Log file list
    img_file = test_files_dir / "cv.png" # Use cv.png instead of test.png
    print(f"test_image_handler: img_file path: {img_file}") # Log img_file path
    
    # Test successful processing
    with patch("PIL.Image.open") as mock_image:
        # Mock image operations
        mock_img = mock_image.return_value.__enter__.return_value
        mock_img.thumbnail = Mock()
        mock_img.save = Mock()
        
        # Process image
        asset_path = ImageHandler.process(img_file)
        
        # Verify temp path
        assert asset_path is not None
        assert isinstance(asset_path, Path)
        assert asset_path.exists()
        
        # Verify image operations
        mock_img.thumbnail.assert_called_once_with((1024, 1024), Image.Resampling.LANCZOS)
        mock_img.save.assert_called_once_with(asset_path, format="PNG") # Use asset_path
    

def test_doc_handler(test_files_dir):
    """Test DocHandler functionality."""
    doc_file = test_files_dir / "doc1.docx"

    # Process document
    temp_path = DocHandler.process(doc_file)

    # Verify temp file was created
    assert temp_path is not None
    assert isinstance(temp_path, Path)
    assert temp_path.exists()
    assert temp_path.suffix == '.txt'

    # Verify text content
    with open(temp_path, 'r', encoding='utf-8') as f:
        content = f.read()
        assert "Shopping List" in content  # Verify expected text is present

    # Cleanup temp file
    temp_path.unlink()

def test_xlsx_handler(test_files_dir):
    """Test XlsxHandler functionality."""
    xlsx_file = test_files_dir / "doc1.xlsx"

    # Process document
    temp_path = XlsxHandler.process(xlsx_file)

    # Verify temp file was created
    assert temp_path is not None
    assert isinstance(temp_path, Path)
    assert temp_path.exists()
    assert temp_path.suffix == '.txt'

    # Verify text content
    with open(temp_path, 'r', encoding='utf-8') as f:
        content = f.read()
        assert "Groceries" in content 

    # Cleanup temp file
    temp_path.unlink()

def test_pdf_handler(test_files_dir):
    """Test PdfHandler functionality."""
    pdf_file = test_files_dir / "cv.pdf"

    # Process PDF
    temp_path = PdfHandler.process(pdf_file)

    # Verify temp path
    assert temp_path is not None
    assert isinstance(temp_path, Path)
    assert temp_path.exists()

    # Verify temp file content has 2 pages
    from PyPDF2 import PdfReader
    reader = PdfReader(temp_path)
    assert len(reader.pages) == 2

def test_handler_extension_lists():
    """Test that handler extension lists are properly defined."""
    # Verify each handler has non-empty extension list
    assert len(ImageHandler.supported_extensions) > 0
    assert len(DocHandler.supported_extensions) > 0
    assert len(XlsxHandler.supported_extensions) > 0
    assert len(PdfHandler.supported_extensions) > 0
    assert len(TextHandler.supported_extensions) > 0
    
    # Verify no duplicate extensions across handlers
    all_extensions = (
        ImageHandler.supported_extensions +
        DocHandler.supported_extensions +
        XlsxHandler.supported_extensions +
        PdfHandler.supported_extensions +
        TextHandler.supported_extensions
    )
    assert len(all_extensions) == len(set(all_extensions))

def test_handler_file_types():
    """Test that handlers have correct file types set."""
    assert ImageHandler.file_type == "image"
    assert DocHandler.file_type == "document"
    assert XlsxHandler.file_type == "spreadsheet"
    assert PdfHandler.file_type == "pdf"
    assert TextHandler.file_type == "text"
