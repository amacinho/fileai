import logging
import os
import tempfile
from PIL import Image
from fileai.pdf_transformer import PDFTransformer
from pathlib import Path
from fileai.config import Asset

class ContentAdapter:
    """Adapts content (images, PDFs, text files) for API upload by handling size and format requirements"""
    
    def __init__(self, client):
        """
        Initialize ContentUploadAdapter with a genai client for file uploads
        
        :param client: google.genai.Client instance
        """
        self.client = client
        
    def adapt_pdf(self, asset: Asset) -> Path:
        """
        Adapt PDF files for API upload by extracting first two pages
        
        :param asset: Asset object containing file information
        :return: Path to temporary file
        """
        pdf_transformer = PDFTransformer()
        with tempfile.NamedTemporaryFile(suffix=asset.path.suffix, delete=False) as temp_file:
            temp_path = temp_file.name
            pdf_transformer.save_first_two_pages(asset.path, temp_path)
        return temp_path
        
    def adapt_image(self, asset: Asset) -> Path:
        """
        Adapt image files for API upload by resizing to acceptable dimensions
        Converts the image to PNG and creates a 1024x1024 thumbnail        
        """
        with Image.open(asset.path) as img:
            img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                temp_path = temp_file.name
                img.save(temp_path, format="PNG")
            return temp_path
        
    def adapt_text(self, asset: Asset) -> Path:
        with open(asset.path, 'r') as asset_file:
            text_content = asset_file.read(5000)  # Truncate to first 5000 chars
        with tempfile.NamedTemporaryFile(suffix=asset.path.suffix, delete=False) as temp_file:
            temp_path = temp_file.name
            with open(temp_path, 'w') as temp_file:
                temp_file.write(text_content)
                return temp_path

    def adapt_content(self, asset: Asset):
        if not asset:
            return None, []
            
        temp_files = []
        try:
            if asset.type == 'pdf':
                temp_path = self.adapt_pdf(asset)
            elif asset.type == 'image':
                temp_path = self.adapt_image(asset)
            elif asset.type == 'text':
                temp_path = self.adapt_text(asset)
            else:
                raise ValueError(f"Unsupported content type: {asset.type}")
            
            temp_files.append(temp_path)
            asset.temp_path = temp_path
            return asset, temp_files
                
        except Exception as err:
            # Clean up temp files on error
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except Exception as e:
                    logging.error(f"Error cleaning up temporary file {temp_file}: {str(e)}")
            raise Exception(f"Content adaptation error: {str(err)}")
