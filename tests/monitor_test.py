import threading
import time
import unittest
import tempfile
import shutil
import base64
import json
from pathlib import Path
from collections import namedtuple
from unittest.mock import Mock
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
        self.pdf_base64 = "JVBERi0xLjEKJcKlwrHDqwoKMSAwIG9iagogIDw8IC9UeXBlIC9DYXRhbG9nCiAgICAgL1BhZ2VzIDIgMCBSCiAgPj4KZW5kb2JqCgoyIDAgb2JqCiAgPDwgL1R5cGUgL1BhZ2VzCiAgICAgL0tpZHMgWzMgMCBSXQogICAgIC9Db3VudCAxCiAgICAgL01lZGlhQm94IFswIDAgMzAwIDE0NF0KICA+PgplbmRvYmoKCjMgMCBvYmoKICA8PCAgL1R5cGUgL1BhZ2UKICAgICAgL1BhcmVudCAyIDAgUgogICAgICAvUmVzb3VyY2VzCiAgICAgICA8PCAvRm9udAogICAgICAgICAgIDw8IC9GMQogICAgICAgICAgICAgICA8PCAvVHlwZSAvRm9udAogICAgICAgICAgICAgICAgICAvU3VidHlwZSAvVHlwZTEKICAgICAgICAgICAgICAgICAgL0Jhc2VGb250IC9UaW1lcy1Sb21hbgogICAgICAgICAgICAgICA+PgogICAgICAgICAgID4+CiAgICAgICA+PgogICAgICAvQ29udGVudHMgNCAwIFIKICA+PgplbmRvYmoKCjQgMCBvYmoKICA8PCAvTGVuZ3RoIDU1ID4+CnN0cmVhbQogIEJUCiAgICAvRjEgMTggVGYKICAgIDAgMCBUZAogICAgKEhlbGxvIFdvcmxkKSBUagogIEVUCmVuZHN0cmVhbQplbmRvYmoKCnhyZWYKMCA1CjAwMDAwMDAwMDAgNjU1MzUgZiAKMDAwMDAwMDAxOCAwMDAwMCBuIAowMDAwMDAwMDc3IDAwMDAwIG4gCjAwMDAwMDAxNzggMDAwMDAgbiAKMDAwMDAwMDQ1NyAwMDAwMCBuIAp0cmFpbGVyCiAgPDwgIC9Sb290IDEgMCBSCiAgICAgIC9TaXplIDUKICA+PgpzdGFydHhyZWYKNTY1CiUlRU9GCg=="
        self.png_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z/C/HgAGgwJ/lK3Q6wAAAABJRU5ErkJggg=="
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
        
        # Create monitor without processing existing files
        self.monitor = Monitor(self.watch_dir, self.output_dir, self.api)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_monitor_new_files(self):
        """Test monitoring new files."""
        # Create test files
        data_dir = self.watch_dir / Path('afolder')
        data_dir.mkdir()
        png_file = data_dir / "test1.png"
        pdf_file = data_dir / "test2.pdf"
        

        
        # Create a new monitor instance
        monitor = Monitor(self.watch_dir, self.output_dir, self.api)
        # Start monitoring in a thread
        monitor_thread = threading.Thread(target=monitor.start_monitoring)
        monitor_thread.daemon = True  # Thread will be killed when main thread exits
        monitor_thread.start()
        time.sleep(1)
        self.assertTrue(monitor._running, "Monitor should be running")
        
        # Store file contents before processing
        png_data = base64.b64decode(self.png_base64)
        pdf_data = base64.b64decode(self.pdf_base64)
        
        # Write files
        with open(png_file, "wb") as f:
            f.write(png_data)
        with open(pdf_file, "wb") as f:
            f.write(pdf_data)
            
        time.sleep(1)

        # Verify files were processed to correct location
        car_folder = self.output_dir / "car"
        self.assertTrue(car_folder.exists(), "Car folder should be created")
        processed_files = list(car_folder.glob("*"))
        self.assertEqual(len(processed_files), 2, "Two files should be processed")

        # Verify file contents
        for processed_file in processed_files:
            with open(processed_file, 'rb') as f:
                processed_content = f.read()
                if processed_file.name.startswith('test1'):
                    self.assertEqual(processed_content, png_data, "PNG content mismatch")
                elif processed_file.name.startswith('test2'):
                    self.assertEqual(processed_content, pdf_data, "PDF content mismatch")

        # Verify original files are removed
        self.assertFalse(png_file.exists(), "Original PNG file should be removed")
        self.assertFalse(pdf_file.exists(), "Original PDF file should be removed")
        self.assertFalse(data_dir.exists(), "Empty data directory should be removed")

        monitor.stop()
        time.sleep(1)
        self.assertFalse(monitor._running, "Monitor should not be running")
        
    def test_monitor_large_file(self):
        """Test monitoring a large file being written in chunks."""
        # Create test file path
        large_file = self.watch_dir / "large_file.txt"
        
        # Create a new monitor instance
        monitor = Monitor(self.watch_dir, self.output_dir, self.api)
        # Start monitoring in a thread
        monitor_thread = threading.Thread(target=monitor.start_monitoring)
        monitor_thread.daemon = True  # Thread will be killed when main thread exits
        monitor_thread.start()
        time.sleep(1)
        self.assertTrue(monitor._running, "Monitor should be running")
        
        # Generate and store file content
        file_content = ""
        chunk_size = 1024 * 1024  # 1MB chunks
        num_chunks = 5    # Total 100KB
        for i in range(num_chunks):
            chunk = f"Chunk {i + 1} content: " + "x" * (chunk_size - 20) + "\n"
            file_content += chunk
            
        # Write large file in chunks
        with open(large_file, "w") as f:
            for i in range(num_chunks):
                chunk = file_content.split('\n')[i] + '\n'
                f.write(chunk)
                f.flush()
                time.sleep(0.05)  # Wait between chunks
        
        time.sleep(2)  # Give monitor time to process
        
        # Verify files were processed to correct location
        car_folder = self.output_dir / "car"
        self.assertTrue(car_folder.exists(), "Car folder should be created")
        processed_files = list(car_folder.glob("*"))
        self.assertEqual(len(processed_files), 1, "One file should be processed")

        # Verify file contents
        processed_file = processed_files[0]
        with open(processed_file, 'r') as f:
            self.assertEqual(f.read(), file_content, "Content mismatch for large file")

        # Verify original file is removed
        self.assertFalse(large_file.exists(), "Original large file should be removed")

        monitor.stop()
        time.sleep(1)
        self.assertFalse(monitor._running, "Monitor should not be running")
        
    def test_process_existing_files_only(self):
        """Test processing existing files without monitoring."""
        # Create test files
        png_file = self.watch_dir / "test1.png"
        pdf_file = self.watch_dir / "test2.pdf"
        
                # Base64-encoded 1x1 PNG image
        

        # Store file contents before processing
        png_data = base64.b64decode(self.png_base64)
        pdf_data = base64.b64decode(self.pdf_base64)
        
        # Write files
        with open(png_file, "wb") as f:
            f.write(png_data)
        with open(pdf_file, "wb") as f:
            f.write(pdf_data)
            
        # Create a new monitor instance
        monitor = Monitor(self.watch_dir, self.output_dir, self.api)
        
        # Process existing files only (without starting monitoring)
        monitor.process_existing_files()
        
        # Verify files were processed to correct location
        car_folder = self.output_dir / "car"
        self.assertTrue(car_folder.exists(), "Car folder should be created")
        processed_files = list(car_folder.glob("*"))
        self.assertEqual(len(processed_files), 2, "Two files should be processed")

        # Verify file contents
        for processed_file in processed_files:
            with open(processed_file, 'rb') as f:
                processed_content = f.read()
                if processed_file.name.startswith('test1'):
                    self.assertEqual(processed_content, png_data, "PNG content mismatch")
                elif processed_file.name.startswith('test2'):
                    self.assertEqual(processed_content, pdf_data, "PDF content mismatch")
        
        # Verify original files are removed
        self.assertFalse(png_file.exists(), "Original PNG file should be removed")
        self.assertFalse(pdf_file.exists(), "Original PDF file should be removed")
        
        # Verify monitor is not running
        self.assertFalse(monitor._running, "Monitor should not be running")

    def test_monitor_nested_folders(self):
        """Test monitoring files in deeply nested folders."""
        # Create a new monitor instance and start monitoring
        monitor = Monitor(self.watch_dir, self.output_dir, self.api)
        monitor_thread = threading.Thread(target=monitor.start_monitoring)
        monitor_thread.daemon = True
        monitor_thread.start()
        time.sleep(1)
        self.assertTrue(monitor._running, "Monitor should be running")

        # Create nested folders and file
        level1_dir = self.watch_dir / "folder1"
        level2_dir = level1_dir / "folder2"
        level2_dir.mkdir(parents=True)
        png_file = level2_dir / "test.png"

        # Write test file
        png_data = base64.b64decode(self.png_base64)
        with open(png_file, "wb") as f:
            f.write(png_data)
        
        time.sleep(1)

        # Verify file was processed
        car_folder = self.output_dir / "car"
        self.assertTrue(car_folder.exists(), "Car folder should be created")
        processed_files = list(car_folder.glob("*"))
        self.assertEqual(len(processed_files), 1, "One file should be processed")

        # Verify original file and folders are removed
        self.assertFalse(png_file.exists(), "Original PNG file should be removed")
        self.assertFalse(level2_dir.exists(), "Level 2 directory should be removed")
        self.assertFalse(level1_dir.exists(), "Level 1 directory should be removed")
        self.assertTrue(self.watch_dir.exists(), "Watch directory should still exist")

        monitor.stop()
        time.sleep(1)
        self.assertFalse(monitor._running, "Monitor should not be running")

    def test_monitor_mixed_files(self):
        """Test monitoring supported and unsupported files."""
        # Create a new monitor instance and start monitoring
        monitor = Monitor(self.watch_dir, self.output_dir, self.api)
        monitor_thread = threading.Thread(target=monitor.start_monitoring)
        monitor_thread.daemon = True
        monitor_thread.start()
        time.sleep(1)
        self.assertTrue(monitor._running, "Monitor should be running")

        # Create test folder and files
        test_dir = self.watch_dir / "test_folder"
        test_dir.mkdir()
        dat_file = test_dir / "test.dat"
        png_file = test_dir / "test.png"

        # Write test files
        with open(dat_file, "wb") as f:
            f.write(b"test data")
        png_data = base64.b64decode(self.png_base64)
        with open(png_file, "wb") as f:
            f.write(png_data)
        
        time.sleep(1)

        # Verify only PNG was processed
        car_folder = self.output_dir / "car"
        self.assertTrue(car_folder.exists(), "Car folder should be created")
        processed_files = list(car_folder.glob("*"))
        self.assertEqual(len(processed_files), 1, "One file should be processed")

        # Verify PNG was removed but DAT remains
        self.assertFalse(png_file.exists(), "PNG file should be removed")
        self.assertTrue(dat_file.exists(), "DAT file should still exist")
        self.assertTrue(test_dir.exists(), "Test directory should still exist")

        monitor.stop()
        time.sleep(1)
        self.assertFalse(monitor._running, "Monitor should not be running")

    def test_process_mixed_files_no_monitor(self):
        """Test processing existing supported and unsupported files without monitoring."""
        # Create test folders and files
        folder1 = self.watch_dir / "folder1"
        folder1.mkdir()
        folder2 = self.watch_dir / "folder2"
        folder2.mkdir()

        dat_file = folder1 / "test.dat"
        with open(dat_file, "wb") as f:
            f.write(b"test data")

        png_file = folder2 / "test.png"
        png_data = base64.b64decode(self.png_base64)
        with open(png_file, "wb") as f:
            f.write(png_data)

        # Create monitor and process existing files
        monitor = Monitor(self.watch_dir, self.output_dir, self.api)
        monitor.process_existing_files()

        # Verify only PNG was processed
        car_folder = self.output_dir / "car"
        self.assertTrue(car_folder.exists(), "Car folder should be created")
        processed_files = list(car_folder.glob("*"))
        self.assertEqual(len(processed_files), 1, "One file should be processed")

        # Verify PNG folder was removed but DAT folder remains
        self.assertFalse(png_file.exists(), "PNG file should be removed")
        self.assertFalse(folder2.exists(), "PNG folder should be removed")
        self.assertTrue(dat_file.exists(), "DAT file should still exist")
        self.assertTrue(folder1.exists(), "DAT folder should still exist")

if __name__ == '__main__':
    unittest.main()
