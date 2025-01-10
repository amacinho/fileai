import logging
import os
import tempfile
from PIL import Image
from fileai.pdf_transformer import PDFTransformer

class ContentAdapter:
    """Adapts content (images, PDFs, text files) for API upload by handling size and format requirements"""
    
    def __init__(self, client):
        """
        Initialize ContentUploadAdapter with a genai client for file uploads
        
        :param client: google.genai.Client instance
        """
        self.client = client
        
    def adapt_pdf(self, asset, temp_path):
        """
        Adapt PDF files for API upload by extracting first two pages
        
        :param asset: Asset object containing file information
        :param temp_path: Path to save adapted file
        :return: str mime_type
        """
        pdf_transformer = PDFTransformer()
        pdf_transformer.save_first_two_pages(asset.path, temp_path)
        return 'application/pdf'
        
    def adapt_image(self, asset, temp_path):
        """
        Adapt image files for API upload by resizing to acceptable dimensions
        
        :param asset: Asset object containing file information
        :param temp_path: Path to save adapted file
        :return: str mime_type
        """
        with Image.open(asset.path) as img:
            img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            img.save(temp_path)
        
        file_extension = os.path.splitext(asset.path)[1].lower()
        if file_extension in ('.jpg', '.jpeg'):
            return 'image/jpeg'
        elif file_extension == '.png':
            return 'image/png'
        return asset.mime_type
        
    def adapt_text(self, asset, temp_path):
        """
        Adapt text files for API upload by truncating to acceptable length
        
        :param asset: Asset object containing file information
        :param temp_path: Path to save adapted file
        :return: str mime_type
        """
        with open(asset.path, 'r') as asset_file:
            text_content = asset_file.read(5000)  # Truncate to first 5000 chars
        with open(temp_path, 'w') as temp_file:
            temp_file.write(text_content)
        return 'text/plain'

    def adapt_content(self, asset):
        """
        Adapt content for API upload by handling size and format requirements
        
        :param asset: Asset object containing file information
        :return: tuple(Asset, list of temp files to cleanup)
        """
        if not asset:
            return None, []
            
        temp_files = []
        try:
            file_extension = os.path.splitext(asset.path)[1].lower()
            
            with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
                temp_path = temp_file.name
                temp_files.append(temp_path)
                
                # Adapt content based on type
                if asset.type == 'pdf':
                    mime_type = self.adapt_pdf(asset, temp_path)
                elif asset.type == 'image':
                    mime_type = self.adapt_image(asset, temp_path)
                elif asset.type == 'text':
                    mime_type = self.adapt_text(asset, temp_path)
                else:
                    raise ValueError(f"Unsupported content type: {asset.type}")

                # Return adapted asset
                asset.temp_path = temp_path
                asset.mime_type = mime_type
                return asset, temp_files
                
        except Exception as err:
            # Clean up temp files on error
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except Exception as e:
                    logging.error(f"Error cleaning up temporary file {temp_file}: {str(e)}")
            raise Exception(f"Content adaptation error: {str(err)}")
