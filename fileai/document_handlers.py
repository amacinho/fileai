import io
import logging
from pathlib import Path
from typing import Optional
import pandas as pd
from docx import Document as DocxDocument
import pdfplumber
from PIL import Image

from fileai.config import Asset

class BaseDocumentHandler:
    """Base class for document handlers"""
    supported_extensions: list = []
    file_type: str = "generic"
    
    @classmethod
    def supported_extension(cls, ext: str) -> bool:
        return ext.lower() in cls.supported_extensions
    
    @classmethod
    def process(cls, file_path: Path) -> Optional[Asset]:
        raise NotImplementedError

    @classmethod
    def create_temp_file(cls, suffix: str) -> Path:
        """Create a temporary file with the given suffix.
        
        Args:
            suffix: The file extension for the temporary file
            
        Returns:
            Path to the temporary file
        """
        import tempfile
        temp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        return Path(temp.name)

class ImageHandler(BaseDocumentHandler):
    """Handles image file processing and metadata extraction"""
    supported_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.tif', '.webp']
    file_type = "image"
    
    @classmethod
    def process(cls, file_path: Path) -> Optional[Asset]:
        try:
            # Open and resize image
            with Image.open(file_path) as img:
                # Create temp file
                temp_path = cls.create_temp_file('.png')
                # Resize image to 1024x1024 max
                img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
                # Save to temp file
                img.save(temp_path, format="PNG")
                # Create asset with temp path
                return Asset(path=file_path, file_type=cls.file_type, temp_path=temp_path)
        except Exception as e:
            logging.error(f"Error processing image {file_path}: {e}")
            logging.error(f"ImageHandler: file_path: {file_path}") # Log file_path
            logging.error(f"Exception type: {type(e)}") # Log exception type
            logging.error(f"Exception message: {e}") # Log exception message
            return None

class DocHandler(BaseDocumentHandler):
    """Handles Microsoft Word document processing"""
    supported_extensions = ['.doc', '.docx']
    file_type = "document"
    
    @classmethod
    def process(cls, file_path: Path) -> Optional[Asset]:
        try:
            # Extract text from document
            doc = DocxDocument(file_path)
            text = "\n".join([para.text for para in doc.paragraphs])
            
            # Create temp file and write content
            temp_path = cls.create_temp_file('.txt')
            with open(temp_path, 'w') as f:
                f.write(text)
            
            # Create asset with temp path
            return Asset(path=file_path, file_type=cls.file_type, temp_path=temp_path)
            
        except Exception as e:
            logging.error(f"Error processing Word document {file_path}: {e}")
            return None

class XlsxHandler(BaseDocumentHandler):
    """Handles Excel spreadsheet processing"""
    supported_extensions = ['.xlsx']
    file_type = "spreadsheet"
    
    @classmethod
    def process(cls, file_path: Path) -> Optional[Asset]:
        try:
            # Read Excel file and convert to string
            df = pd.read_excel(file_path, sheet_name=0)
            text = df.to_string()
            logging.info(f"Converted DataFrame to string. Text length: {len(text) if text else 0}")
            
            # Create temp file and write content
            temp_path = cls.create_temp_file('.txt')
            with open(temp_path, 'w') as f:
                f.write(text)
            
            # Create asset with temp path
            return Asset(path=file_path, file_type=cls.file_type, temp_path=temp_path)
            
        except Exception as e:
            logging.error(f"Error processing Excel file {file_path}: {e}")
            logging.error(f"Exception type: {type(e)}")
            logging.error(f"Exception message: {str(e)}")
            return None

class PdfHandler(BaseDocumentHandler):
    supported_extensions = ['.pdf']
    file_type = "pdf"
    
    @classmethod
    def process(cls, file_path: Path) -> Optional[Asset]:
        try:
            # Extract text from PDF
            with pdfplumber.open(file_path) as pdf:
                text = "\n".join([page.extract_text() for page in pdf.pages])
            
            # Create temp file and write content
            temp_path = cls.create_temp_file('.txt')
            with open(temp_path, 'w') as f:
                f.write(text)
            
            # Create asset with temp path
            return Asset(path=file_path, file_type=cls.file_type, temp_path=temp_path)
            
        except Exception as e:
            logging.error(f"Error processing PDF {file_path}: {e}")
            return None

class TextHandler(BaseDocumentHandler):
    """Handles plain text file processing"""
    supported_extensions = ['.txt', '.text', '.rtf', '.csv', '.tsv']
    file_type = "text"

    @classmethod
    def process(cls, file_path: Path) -> Optional[Asset]:
        try:
            # Read original file
            with open(file_path, 'r') as f:
                text = f.read()
            
            # Create temp file and write content
            temp_path = cls.create_temp_file(file_path.suffix)
            with open(temp_path, 'w') as f:
                f.write(text)
            
            # Create asset with temp path
            return Asset(path=file_path, file_type=cls.file_type, temp_path=temp_path)
            
        except Exception as e:
            logging.error(f"Error processing text file {file_path}: {e}")
            return None

def get_handler(extension: str) -> Optional[type[BaseDocumentHandler]]:
    """Factory function to get the appropriate handler class for a file extension.
    
    This follows the Factory Pattern where the factory returns handler classes rather than instances.
    The returned class can then be used to call class methods like process() or create instances
    if needed.
    
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
