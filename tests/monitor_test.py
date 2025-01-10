import unittest
import tempfile
import shutil
import time
import os
import json
import logging
import threading
from pathlib import Path
from collections import namedtuple
from unittest.mock import Mock, patch
from fileai.main import Monitor
from fileai.api import GeminiAPI

UploadResponse = namedtuple('UploadResponse', ['uri'])

class MonitorTest(unittest.TestCase):
    def setUp(self):
        # Create temporary directories for testing
        self.temp_dir = tempfile.mkdtemp()
        self.watch_dir = Path(self.temp_dir) / "watch"
        self.output_dir = Path(self.temp_dir) / "output"
        self.watch_dir.mkdir()
        self.output_dir.mkdir()

        # Mock API responses
        mock_response = Mock()
        mock_response.text = json.dumps({
            "doc_type": "invoice",
            "doc_date": "2016-01-01",
            "doc_topic": "car insurance",
            "doc_owner": "John",
            "doc_folder": "car",
            "doc_keywords": ["car", "insurance", "invoice", "payment"]
        })
        
        # Initialize API with mocks
        self.api = GeminiAPI()
        self.api.client = Mock()
        self.api.client.models = Mock()
        self.api.client.models.generate_content = Mock(return_value=mock_response)
        self.api.client.files = Mock()
        self.api.client.files.upload = Mock(return_value=UploadResponse(uri="file://output.jpg"))
        
        # Create monitor
        self.monitor = Monitor(self.watch_dir, self.output_dir, self.api, poll_interval=0.1)
        self.monitor.start()

    def tearDown(self):
        self.monitor.stop()
        shutil.rmtree(self.temp_dir)

    def test_large_file_handling(self):
        """Test handling of a large file being written in chunks."""
        test_file = self.watch_dir / "large_file.dat"
        
        # Create large random data
        chunk_size = 1024 * 1024  # 1MB chunks
        total_size = chunk_size * 5  # 5MB total
        data = os.urandom(total_size)
        
        def write_chunks():
            with open(test_file, 'wb') as f:
                for i in range(0, total_size, chunk_size):
                    chunk = data[i:i + chunk_size]
                    f.write(chunk)
                    f.flush()
                    time.sleep(0.5)  # Simulate slow write
        
        # Write file in separate thread
        writer = threading.Thread(target=write_chunks)
        writer.start()
        writer.join(timeout=30)
        self.assertFalse(writer.is_alive(), "File write should complete")
        
        # Wait for processing with timeout
        max_wait = 30
        start_time = time.time()
        car_folder = self.output_dir / "car"
        
        while time.time() - start_time < max_wait:
            if car_folder.exists() and any(car_folder.glob("*")):
                break
            time.sleep(0.5)
        
        self.assertTrue(car_folder.exists(), "Car folder should be created")
        self.assertTrue(any(car_folder.glob("*")), "File should be moved to car folder")
        self.api.client.models.generate_content.assert_called()

    def test_pdf_handling(self):
        """Test handling of a PDF file."""
        test_file = self.watch_dir / "test.pdf"
        
        # Create minimal valid PDF
        pdf_content = b'''%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 3 3]>>endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000052 00000 n
0000000101 00000 n
trailer<</Size 4/Root 1 0 R>>
startxref
149
%%EOF'''
        
        with open(test_file, 'wb') as f:
            f.write(pdf_content)
        
        # Wait for processing with timeout
        max_wait = 10
        start_time = time.time()
        car_folder = self.output_dir / "car"
        
        while time.time() - start_time < max_wait:
            if car_folder.exists() and any(car_folder.glob("*")):
                break
            time.sleep(0.5)
        
        self.assertTrue(car_folder.exists(), "Car folder should be created")
        moved_file = next(car_folder.glob("*"))
        self.assertTrue(moved_file.exists(), "File should be moved to car folder")
        self.assertIn("car-insurance", moved_file.name.lower(), "Filename should contain topic")
        self.api.client.models.generate_content.assert_called()

    def test_png_handling(self):
        """Test handling of a PNG file."""
        test_file = self.watch_dir / "test.png"
        
        # Create minimal valid PNG
        png_content = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\x0DIHDR\x00\x00\x00\x01\x00'
                      b'\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00'
                      b'\x0AIDAT\x08\x99c\x00\x00\x00\x02\x00\x01\xe5\x27\xde\xfc\x00'
                      b'\x00\x00\x00IEND\xaeB`\x82')
        
        with open(test_file, 'wb') as f:
            f.write(png_content)
        
        # Wait for processing with timeout
        max_wait = 10
        start_time = time.time()
        car_folder = self.output_dir / "car"
        
        while time.time() - start_time < max_wait:
            if car_folder.exists() and any(car_folder.glob("*")):
                break
            time.sleep(0.5)
        
        self.assertTrue(car_folder.exists(), "Car folder should be created")
        moved_file = next(car_folder.glob("*"))
        self.assertTrue(moved_file.exists(), "File should be moved to car folder")
        self.assertIn("car-insurance", moved_file.name.lower(), "Filename should contain topic")
        self.api.client.models.generate_content.assert_called()

if __name__ == '__main__':
    unittest.main()
