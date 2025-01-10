from pdf2image import convert_from_path
import base64
from io import BytesIO
from PyPDF2 import PdfReader, PdfWriter
import os


class PDFTransformer:
    def __init__(self):
        """
        Initialize the PDFTransformer class.
        """
        pass

    def save_first_two_pages(self, pdf_path, output_path):
        """
        Create a new PDF with just the first two pages and save it to output_path.
        
        :param pdf_path: Path to the source PDF file
        :param output_path: Path where to save the new PDF
        :return: None
        """
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        
        # Add up to first two pages
        for i in range(min(2, len(reader.pages))):
            writer.add_page(reader.pages[i])
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Write the output file
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)
