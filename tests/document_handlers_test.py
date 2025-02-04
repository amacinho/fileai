import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
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
    expected_content = "Shopping list  2025 February 02\n\nApples\nOranges\nButter\n"
    
    # Test successful processing
    with patch("tempfile.NamedTemporaryFile") as mock_tempfile:
        mock_file = mock_tempfile.return_value.__enter__.return_value
        mock_file.name = str(Path("mock_temp_path"))
        asset = TextHandler.process(text_file)
        
        # Verify asset
        assert asset is not None
        assert asset.type == "text"
        assert asset.temp_path == Path("mock_temp_path")
        
        # Verify temp file content
        with patch("builtins.open", mock_open()) as mock_open_file:
            TextHandler.process(text_file)
            mock_open_file.return_value.write.assert_called_once_with(expected_content)
    
    # Test error handling with non-existent file
    asset = TextHandler.process(test_files_dir / "nonexistent.txt")
    assert asset is None

def test_image_handler(test_files_dir):
    """Test ImageHandler functionality."""
    print(f"Files in test_image_handler temp dir: {os.listdir(test_files_dir)}") # Log file list
    img_file = test_files_dir / "cv.png" # Use cv.png instead of test.png
    print(f"test_image_handler: img_file path: {img_file}") # Log img_file path
    
    # Test successful processing
    with patch("tempfile.NamedTemporaryFile") as mock_tempfile, \
         patch("PIL.Image.open") as mock_image:
        # Mock temp file
        mock_file = mock_tempfile.return_value.__enter__.return_value
        mock_file.name = str(Path("mock_temp_path"))
        
        # Mock image operations
        mock_img = mock_image.return_value.__enter__.return_value
        mock_img.thumbnail = Mock()
        mock_img.save = Mock()
        
        # Process image
        asset = ImageHandler.process(img_file)
        
        # Verify asset
        assert asset is not None
        assert asset.type == "image"
        assert asset.temp_path == Path("mock_temp_path")
        
        # Verify image operations
        mock_img.thumbnail.assert_called_once_with((1024, 1024), Image.Resampling.LANCZOS)
        mock_img.save.assert_called_once_with(Path("mock_temp_path"), format="PNG")
    
    # Test error handling with invalid image
    invalid_img = test_files_dir / "invalid.png"
    invalid_img.write_text("Not an image")
    asset = ImageHandler.process(invalid_img)
    assert asset is None


def test_doc_handler(test_files_dir):
    """Test DocHandler functionality."""
    doc_file = test_files_dir / "doc1.docx"
    expected_text = "Test document content"
    
    with patch("tempfile.NamedTemporaryFile") as mock_tempfile, \
         patch("docx.Document") as mock_docx:
        # Mock temp file
        mock_file = mock_tempfile.return_value.__enter__.return_value
        mock_file.name = str(Path("mock_temp_path"))
        
        # Mock docx content
        mock_doc = mock_docx.return_value
        mock_doc.paragraphs = [Mock(text=expected_text)]
        
        # Process document
        asset = DocHandler.process(doc_file)
        
        # Verify asset
        assert asset is not None
        assert asset.type == "doc"
        assert asset.temp_path == Path("mock_temp_path")
        
        # Verify temp file content
        with patch("builtins.open", mock_open()) as mock_open_file:
            DocHandler.process(doc_file)
            mock_open_file.return_value.write.assert_called_once_with(expected_text)

def test_xlsx_handler(test_files_dir):
    """Test XlsxHandler functionality."""
    xlsx_file = test_files_dir / "doc1.xlsx"
    expected_text = "Test spreadsheet content"
    
    with patch("tempfile.NamedTemporaryFile") as mock_tempfile, \
         patch("pandas.read_excel") as mock_read_excel:
        # Mock temp file
        mock_file = mock_tempfile.return_value.__enter__.return_value
        mock_file.name = str(Path("mock_temp_path"))
        
        # Mock pandas DataFrame
        mock_df = Mock()
        mock_df.to_string.return_value = expected_text
        mock_read_excel.return_value = mock_df
        
        # Process spreadsheet
        asset = XlsxHandler.process(xlsx_file)
        
        # Verify asset
        assert asset is not None
        assert asset.type == "spreadsheet"
        assert asset.temp_path == Path("mock_temp_path")
        
        # Verify temp file content
        with patch("builtins.open", mock_open()) as mock_open_file:
            XlsxHandler.process(xlsx_file)
            mock_open_file.return_value.write.assert_called_once_with(expected_text)

def test_pdf_handler(test_files_dir):
    """Test PdfHandler functionality."""
    pdf_file = test_files_dir / "cv.pdf"
    expected_text = "Test PDF content"
    
    with patch("tempfile.NamedTemporaryFile") as mock_tempfile, \
         patch("pdfplumber.open") as mock_pdf_open:
        # Mock temp file
        mock_file = mock_tempfile.return_value.__enter__.return_value
        mock_file.name = str(Path("mock_temp_path"))
        
        # Mock PDF content
        mock_pdf = mock_pdf_open.return_value.__enter__.return_value
        mock_page = Mock()
        mock_page.extract_text.return_value = expected_text
        mock_pdf.pages = [mock_page]
        
        # Process PDF
        asset = PdfHandler.process(pdf_file)
        
        # Verify asset
        assert asset is not None
        assert asset.type == "pdf"
        assert asset.temp_path == Path("mock_temp_path")
        
        # Verify temp file content
        with patch("builtins.open", mock_open()) as mock_open_file:
            PdfHandler.process(pdf_file)
            mock_open_file.return_value.write.assert_called_once_with(expected_text)

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
