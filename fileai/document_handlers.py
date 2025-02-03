import io
import logging
from pathlib import Path
from typing import Optional, Tuple
import pandas as pd
from docx import Document as DocxDocument
import PyPDF2
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
    def process(cls, file_path: Path) -> Tuple[Optional[str], Optional[Asset]]:
        raise NotImplementedError

class ImageHandler(BaseDocumentHandler):
    """Handles image file processing and metadata extraction"""
    supported_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.tif', '.webp']
    file_type = "image"
    
    @classmethod
    def process(cls, file_path: Path) -> Tuple[Optional[str], Optional[Asset]]:
        try:
            with Image.open(file_path):
                asset = Asset(path=file_path, file_type=cls.file_type)
                return "", asset
        except Exception as e:
            logging.error(f"Error processing image {file_path}: {e}")
            logging.error(f"ImageHandler: file_path: {file_path}") # Log file_path
            logging.error(f"Exception type: {type(e)}") # Log exception type
            logging.error(f"Exception message: {e}") # Log exception message
            return None, None

class DocHandler(BaseDocumentHandler):
    """Handles Microsoft Word document processing"""
    supported_extensions = ['.doc', '.docx']
    file_type = "document"
    
    @classmethod
    def process(cls, file_path: Path) -> Tuple[Optional[str], Optional[Asset]]:
        try:
            doc = DocxDocument(file_path)
            text = "\n".join([para.text for para in doc.paragraphs])
            asset = Asset(path=file_path, file_type=cls.file_type)
            return text, asset
        except Exception as e:
            logging.error(f"Error processing Word document {file_path}: {e}")
            return None, None

class XlsxHandler(BaseDocumentHandler):
    """Handles Excel spreadsheet processing"""
    supported_extensions = ['.xlsx']
    file_type = "spreadsheet"
    
    @classmethod
    def process(cls, file_path: Path) -> Tuple[Optional[str], Optional[Asset]]:
        try:
            logging.info(f"Attempting to read Excel file: {file_path}")
            df = pd.read_excel(file_path, sheet_name=0)
            logging.info(f"Successfully read Excel file. DataFrame shape: {df.shape}")
            text = df.to_string()
            logging.info(f"Converted DataFrame to string. Text length: {len(text) if text else 0}")
            asset = Asset(path=file_path, file_type=cls.file_type)
            return text, asset
        except Exception as e:
            logging.error(f"Error processing Excel file {file_path}: {e}")
            logging.error(f"Exception type: {type(e)}")
            logging.error(f"Exception message: {str(e)}")
            return None, None

class PdfHandler(BaseDocumentHandler):
    """Handles PDF document processing"""
    supported_extensions = ['.pdf']
    file_type = "document"
    
    @classmethod
    def process(cls, file_path: Path) -> Tuple[Optional[str], Optional[Asset]]:
        try:
            with pdfplumber.open(file_path) as pdf:
                text = "\n".join([page.extract_text() for page in pdf.pages])
            asset = Asset(path=file_path, file_type=cls.file_type)
            return text, asset
        except Exception as e:
            logging.error(f"Error processing PDF {file_path}: {e}")
            return None, None

class TextHandler(BaseDocumentHandler):
    """Handles plain text file processing"""
    supported_extensions = ['.txt', '.text', '.rtf', '.csv', '.tsv']
    file_type = "text"

    @classmethod
    def process(cls, file_path: Path) -> Tuple[Optional[str], Optional[Asset]]:
        try:
            with open(file_path, 'r') as f:
                text = f.read()
            asset = Asset(path=file_path, file_type=cls.file_type)
            return text, asset
        except Exception as e:
            logging.error(f"Error processing text file {file_path}: {e}")
            return None, None

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
