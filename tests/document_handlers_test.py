import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from PIL import Image
import io
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
    
    # Test case insensitivity
    assert get_handler('.JPG') == ImageHandler
    assert get_handler('.PDF') == PdfHandler
    
    # Test unsupported extension
    assert get_handler('.unsupported') is None

def test_text_handler(test_files_dir):
    """Test TextHandler functionality."""
    text_file = test_files_dir / "test.txt"
    
    # Test successful processing
    text, asset = TextHandler.process(text_file)
    expected_content = "Shopping list  2025 February 02\n\nApples\nOranges\nButter\n".strip()
    assert text == expected_content
    assert asset.type == "text"
    
    # Test error handling with non-existent file
    text, asset = TextHandler.process(test_files_dir / "nonexistent.txt")
    assert text is None
    assert asset is None

def test_image_handler(test_files_dir):
    """Test ImageHandler functionality."""
    print(f"Files in test_image_handler temp dir: {os.listdir(test_files_dir)}") # Log file list
    img_file = test_files_dir / "cv.png" # Use cv.png instead of test.png
    print(f"test_image_handler: img_file path: {img_file}") # Log img_file path
    
    # Test successful processing
    text, asset = ImageHandler.process(img_file)
    assert text is None or text == ""
    assert asset is not None
    assert asset.type == "image"
    
    # Test error handling with invalid image
    invalid_img = test_files_dir / "invalid.png"
    invalid_img.write_text("Not an image")
    text, asset = ImageHandler.process(invalid_img)
    assert text is None
    assert asset is None


def test_doc_handler(test_files_dir):
    """Test DocHandler functionality."""
    doc_file = test_files_dir / "doc1.docx"
    text, asset = DocHandler.process(doc_file)
    assert text is not None
    assert asset.type == "doc"

def test_xlsx_handler(test_files_dir):
    """Test XlsxHandler functionality."""
    xlsx_file = test_files_dir / "doc1.xlsx"
    text, asset = XlsxHandler.process(xlsx_file)
    assert text is not None
    assert asset.type == "spreadsheet"

def test_pdf_handler(test_files_dir):
    """Test PdfHandler functionality."""
    pdf_file = test_files_dir / "cv.pdf"
    text, asset = PdfHandler.process(pdf_file)
    assert text is not None
    assert asset.type == "pdf"

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
    assert PdfHandler.file_type == "document"
    assert TextHandler.file_type == "text"
