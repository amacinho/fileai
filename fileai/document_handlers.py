import logging
from pathlib import Path
from typing import Optional
from PyPDF2 import PdfReader, PdfWriter
from PIL import Image
import shutil
logging.getLogger("PIL").setLevel(logging.INFO)

SUPPORTED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp", ".heic"]
SUPPORTED_DOCUMENT_EXTENSIONS = [".docx", ".doc", ".odt"] 
SUPPPORTED_SPREADSHEET_EXTENSIONS = [".xlsx", ".xls"]
SUPPORTED_TEXT_EXTENSIONS = [".txt", ".csv", ".tsv", ".md", ".html", ".xml", ".json", ".yaml", ".yml", ".rtf"]
SUPPORTED_PDF_EXTENSIONS = [".pdf"]

class BaseDocumentHandler:
    """Base class for document handlers"""
    supported_extensions: list = []
    file_type: str = "generic"
    
    @classmethod
    def supported_extension(cls, ext: str) -> bool:
        return ext.lower() in cls.supported_extensions
    
    @classmethod
    def process(cls, file_path: Path) -> Optional[Path]:

        raise NotImplementedError

    @classmethod
    def create_temp_file(cls, suffix: str) -> Path:
        """Create a temporary file with the given suffix.
        
        This is a utility method used by handlers to create temporary files
        for storing processed content. The temporary file will be used by
        the pipeline for further processing (e.g., categorization).
        
        Args:
            suffix: The file extension for the temporary file (e.g., '.txt', '.png')
            
        Returns:
            Path to the created temporary file. The caller is responsible for
            cleaning up this file when it's no longer needed.
        """
        import tempfile
        temp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        return Path(temp.name)

class ImageHandler(BaseDocumentHandler):
    """Handles image file processing and metadata extraction"""
    supported_extensions = SUPPORTED_IMAGE_EXTENSIONS
    file_type = "image"
    
    @classmethod
    def process(cls, file_path: Path) -> Optional[Path]:
        temporary_path = None
        try:
            # Open and resize image
            with Image.open(file_path) as img:
                temporary_path = cls.create_temp_file('.png')
                img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
                img.save(temporary_path, format="PNG")
                return temporary_path
        except Exception as e:
            logging.error(f"Error processing image {file_path}: {e}")
            raise e

class DocHandler(BaseDocumentHandler):
    """Handles Microsoft Word document processing"""
    supported_extensions = SUPPORTED_DOCUMENT_EXTENSIONS
    file_type = "document"
    
    @classmethod
    def process(cls, file_path: Path) -> Optional[Path]:
        temporary_path = None
        try:
            temporary_path = cls.create_temp_file(file_path.suffix)
            shutil.copy2(file_path, temporary_path)
            return temporary_path
        except Exception as e:
            logging.error(f"Error processing Word document {file_path}: {e}")
            raise e
class XlsxHandler(BaseDocumentHandler):
    """Handles Excel spreadsheet processing"""
    supported_extensions = SUPPPORTED_SPREADSHEET_EXTENSIONS
    file_type = "spreadsheet"

    @classmethod
    def process(cls, file_path: Path) -> Optional[Path]:
        temporary_path = None
        try:
            temporary_path = cls.create_temp_file(file_path.suffix)
            shutil.copy2(file_path, temporary_path)
            return temporary_path
        except Exception as e:
            logging.error(f"Error processing Excel file {file_path}: {e}")
            raise e


class PdfHandler(BaseDocumentHandler):
    supported_extensions = SUPPORTED_PDF_EXTENSIONS
    file_type = "pdf"
    
    @classmethod
    def process(cls, file_path: Path) -> Optional[Path]:
        temporary_path = None
        reader = PdfReader(file_path)
        writer = PdfWriter()
        try:
            # Extract text from PDF
            # Add up to first two pages
            for i in range(min(2, len(reader.pages))):
                writer.add_page(reader.pages[i])
            temporary_path = cls.create_temp_file('.pdf')
            with open(temporary_path, "wb") as output_file:
                writer.write(output_file)
                return temporary_path
        except Exception as e:
            logging.error(f"Error processing PDF {file_path}: {e}")
            return None

class TextHandler(BaseDocumentHandler):
    """Handles plain text file processing"""
    supported_extensions = SUPPORTED_TEXT_EXTENSIONS
    file_type = "text"

    @classmethod
    def process(cls, file_path: Path) -> Optional[Path]:
        try:
            # Read original file
            with open(file_path, 'r') as f:
                text = f.read()
            
            # Create temp file and write content
            temporary_path = cls.create_temp_file(file_path.suffix)
            with open(temporary_path, 'w') as f:
                f.write(text)
                return temporary_path 
        except Exception as e:
            logging.error(f"Error processing text file {file_path}: {e}")
            raise e

def get_handler(extension: str) -> Optional[type[BaseDocumentHandler]]:
    """Factory function to get the appropriate handler class for a file extension.
    
    This follows the Factory Pattern where the factory returns handler classes rather than instances.
    The returned class can then be used to call class methods like process() or create instances
    if needed.
    
    This is typically used by the DocumentPipeline in its extract_content phase to get
    the appropriate handler for processing a document.
    
    Example:
        handler = get_handler('.pdf')
        if handler:
            asset = handler.process(file_path)
    
    Args:
        extension: The file extension to get a handler for (e.g. '.pdf', '.jpg')
        
    Returns:
        The appropriate handler class for the extension, or None if no handler is found
    """
    handlers = [
        ImageHandler,
        DocHandler,
        XlsxHandler,
        PdfHandler,
        TextHandler
    ]
    for handler in handlers:
        if handler.supported_extension(extension.lower()):
            return handler
    return None
