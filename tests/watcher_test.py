import threading
import time
import unittest
import tempfile
import shutil
import base64
import json
from pathlib import Path
import itertools
from collections import namedtuple
from unittest.mock import Mock
from fileai.watcher import Watcher
from fileai.api import GeminiAPI

UploadResponse = namedtuple('UploadResponse', ['uri'])

class WatcherTest(unittest.TestCase):
    def setUp(self):
        # Create temporary directories for testing
        self.temp_dir = tempfile.mkdtemp()
        self.watch_dir = Path(self.temp_dir) / "watch"
        self.output_dir = Path(self.temp_dir) / "output"
        self.watch_dir.mkdir()
        self.output_dir.mkdir()
        
        # Counter for unique hash generation in stress test
        self.hash_counter = 0
        
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
        
        # Increase rate limit for stress test
        self.api.rate_limiter.max_calls = 1000
        
        # Create watcher without processing existing files
        self.watcher = Watcher(self.watch_dir, self.output_dir, self.api)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def _create_test_file(self, path: Path, file_type: str, number: int):
        """Helper to create a test file with specific type and number."""
        if file_type == 'png':
            data = base64.b64decode(self.png_base64)
            filename = f"png{number:02d}.png"
        elif file_type == 'pdf':
            data = base64.b64decode(self.pdf_base64)
            filename = f"pdf{number:02d}.pdf"
        elif file_type == 'dat':
            data = b"test data"
            filename = f"dat{number:02d}.dat"
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
        
        file_path = path / filename
        with open(file_path, "wb") as f:
            f.write(data)
        return file_path

    def _create_stress_test_structure(self, base_dir: Path):
        """Create a complex folder structure with many test files."""
        # Create root folders A
        for root in ['folderA']:
            root_path = base_dir / root
            root_path.mkdir()
            
            # Create 5 files in root
            for i in range(1, 6):
                self._create_test_file(root_path, 'png', i)
                self._create_test_file(root_path, 'pdf', i)
            
            
            for level1 in ['folder1', 'folder2', 'folder3']:
                level1_path = root_path / level1
                level1_path.mkdir()
                
                # Create 5 files in level1
                for i in range(1, 6):
                    self._create_test_file(level1_path, 'png', i)
                    self._create_test_file(level1_path, 'pdf', i)
                
                # Create dat file in folderB/folder1
                if level1 == 'folder1':
                    self._create_test_file(level1_path, 'dat', 1)

                for level2 in ['foldera', 'folderb', 'folderc']:
                    level2_path = level1_path / level2
                    level2_path.mkdir()
                    
                    # Create 5 files in level2
                    for i in range(1, 6):
                        self._create_test_file(level2_path, 'png', i)
                        self._create_test_file(level2_path, 'pdf', i)
                    
                    # Create dat file in folderA/folder1/foldera
                    if root == 'folderA' and level1 == 'folder1' and level2 == 'foldera':
                        self._create_test_file(level2_path, 'dat', 1)

    def test_watcher_new_files(self):
        """Test monitoring new files."""
        # Create test files
        data_dir = self.watch_dir / Path('afolder')
        data_dir.mkdir()
        time.sleep(1)  # Give watchdog time to set up monitoring for new directory
        png_file = data_dir / "test1.png"
        pdf_file = data_dir / "test2.pdf"
        
        # Create a new watcher instance
        watcher = Watcher(self.watch_dir, self.output_dir, self.api)
        # Start monitoring in a thread
        monitor_thread = threading.Thread(target=watcher.start_monitoring)
        monitor_thread.daemon = True  # Thread will be killed when main thread exits
        monitor_thread.start()
        time.sleep(1)
        self.assertTrue(watcher._running, "Watcher should be running")
        
        # Store file contents before processing
        png_data = base64.b64decode(self.png_base64)
        pdf_data = base64.b64decode(self.pdf_base64)
        
        # Write files
        with open(png_file, "wb") as f:
            f.write(png_data)
        with open(pdf_file, "wb") as f:
            f.write(pdf_data)
            
        time.sleep(10)  # Give more time for stability checks

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

        watcher.stop()
        time.sleep(1)
        self.assertFalse(watcher._running, "Watcher should not be running")
        
    def test_watcher_large_file(self):
        """Test monitoring a large file being written in chunks."""
        # Create test file path
        large_file = self.watch_dir / "large_file.txt"
        
        # Create a new watcher instance
        watcher = Watcher(self.watch_dir, self.output_dir, self.api)
        # Start monitoring in a thread
        monitor_thread = threading.Thread(target=watcher.start_monitoring)
        monitor_thread.daemon = True  # Thread will be killed when main thread exits
        monitor_thread.start()
        time.sleep(1)
        self.assertTrue(watcher._running, "Watcher should be running")
        
        # Generate and store file content
        file_content = ""
        chunk_size = 1024 * 1024  # 1MB chunks
        num_chunks = 5    # Total 5MB
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
        
        time.sleep(5)  # Give more time for stability checks
        
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

        watcher.stop()
        time.sleep(1)
        self.assertFalse(watcher._running, "Watcher should not be running")

    def test_process_existing_files_only(self):
        """Test processing existing files without monitoring."""
        # Create test files
        png_file = self.watch_dir / "test1.png"
        pdf_file = self.watch_dir / "test2.pdf"
        
        # Store file contents before processing
        png_data = base64.b64decode(self.png_base64)
        pdf_data = base64.b64decode(self.pdf_base64)
        
        # Write files
        with open(png_file, "wb") as f:
            f.write(png_data)
        with open(pdf_file, "wb") as f:
            f.write(pdf_data)
            
        # Create a new watcher instance
        watcher = Watcher(self.watch_dir, self.output_dir, self.api)
        
        # Process existing files only (without starting monitoring)
        watcher.process_existing_files()
        
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
        
        # Verify watcher is not running
        self.assertFalse(watcher._running, "Watcher should not be running")

    def test_watcher_nested_folders(self):
        """Test monitoring files in deeply nested folders."""
        # Create a new watcher instance and start monitoring
        watcher = Watcher(self.watch_dir, self.output_dir, self.api)
        monitor_thread = threading.Thread(target=watcher.start_monitoring)
        monitor_thread.daemon = True
        monitor_thread.start()
        time.sleep(1)
        self.assertTrue(watcher._running, "Watcher should be running")

        # Create nested folders and file
        level1_dir = self.watch_dir / "folder1" 
        level2_dir = level1_dir / "folder2"
        level2_dir.mkdir(parents=True)
        png_file = level2_dir / "test.png"

        # Write test file
        png_data = base64.b64decode(self.png_base64)
        with open(png_file, "wb") as f:
            f.write(png_data)
        
        time.sleep(5)  # Give more time for stability checks

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

        watcher.stop()
        time.sleep(1)
        self.assertFalse(watcher._running, "Watcher should not be running")

    def test_watcher_mixed_files(self):
        """Test monitoring supported and unsupported files."""
        # Create a new watcher instance and start monitoring
        watcher = Watcher(self.watch_dir, self.output_dir, self.api)
        monitor_thread = threading.Thread(target=watcher.start_monitoring)
        monitor_thread.daemon = True
        monitor_thread.start()
        time.sleep(1)
        self.assertTrue(watcher._running, "Watcher should be running")

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
        
        time.sleep(5)  # Give more time for stability checks

        # Verify only PNG was processed
        car_folder = self.output_dir / "car"
        self.assertTrue(car_folder.exists(), "Car folder should be created")
        processed_files = list(car_folder.glob("*"))
        self.assertEqual(len(processed_files), 1, "One file should be processed")

        # Verify PNG was removed but DAT remains
        self.assertFalse(png_file.exists(), "PNG file should be removed")
        self.assertTrue(dat_file.exists(), "DAT file should still exist")
        self.assertTrue(test_dir.exists(), "Test directory should still exist")

        watcher.stop()
        time.sleep(1)
        self.assertFalse(watcher._running, "Watcher should not be running")

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

        # Create watcher and process existing files
        watcher = Watcher(self.watch_dir, self.output_dir, self.api)
        watcher.process_existing_files()

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

    def test_watcher_stress_test(self):
        """Test monitoring a complex folder structure with many files."""
        # Create test structure in a separate temp directory
        stress_dir = Path(tempfile.mkdtemp())
        try:
            # Create the complex folder structure
            self._create_stress_test_structure(stress_dir)
            
            # Create a new watcher instance with unique hash mock
            watcher = Watcher(self.watch_dir, self.output_dir, self.api)
            
            # Mock categorize_file to return random folders and unique filenames
            folders = ['medical', 'financial', 'travel', 'personal', 'technical', 'legal', 'receipts', 'misc']
            def unique_categorization(options):
                self.hash_counter += 1
                folder = folders[self.hash_counter % len(folders)]
                filename = f"file_{self.hash_counter}"
                return filename, folder
            watcher.organizer.file_renamer.categorize_file = Mock(side_effect=unique_categorization)
            
            # Start monitoring in a thread
            monitor_thread = threading.Thread(target=watcher.start_monitoring)
            monitor_thread.daemon = True
            monitor_thread.start()
            time.sleep(1)
            self.assertTrue(watcher._running, "Watcher should be running")
            
            # Copy entire structure to watch directory
            for item in stress_dir.iterdir():
                shutil.copytree(item, self.watch_dir / item.name)
            
            # Wait for processing
            time.sleep(60)
            
            # Verify all PNG and PDF files are processed
            # Count total processed files across all output folders
            processed_files = []
            folders = ['medical', 'financial', 'travel', 'personal', 'technical', 'legal', 'receipts', 'misc']
            for folder in folders:
                folder_path = self.output_dir / folder
                if folder_path.exists():
                    processed_files.extend(list(folder_path.glob("*")))
            
            # Calculate expected number of files (only PNG and PDF files)
            # In folderA:
            # - 5 files (PNG) + 5 files (PDF) in root = 10 files
            # - 3 subfolders * (5 PNG + 5 PDF) = 30 files
            # - 3 subfolders * 3 subsubfolders * (5 PNG + 5 PDF) = 90 files
            # Total: 130 files
            expected_files = 130
            self.assertEqual(len(processed_files), expected_files,
                           f"Expected {expected_files} processed files")
            
            # Verify files are distributed across folders
            files_per_folder = {folder: len(list((self.output_dir / folder).glob("*")))
                              for folder in folders if (self.output_dir / folder).exists()}
            self.assertTrue(all(count > 0 for count in files_per_folder.values()),
                          "Files should be distributed across folders")
            
            # Verify folders with dat files still exist
            self.assertTrue((self.watch_dir / "folderA" / "folder1" / "foldera").exists(),
                          "folderA/folder1/foldera should exist (contains dat file)")
            self.assertTrue((self.watch_dir / "folderB" / "folder1").exists(),
                          "folderB/folder1 should exist (contains dat file)")
            self.assertTrue((self.watch_dir / "folderC").exists(),
                          "folderC should exist (contains dat file)")
            
            # Verify dat files still exist
            self.assertTrue((self.watch_dir / "folderA" / "folder1" / "foldera" / "dat01.dat").exists(),
                          "dat file in folderA/folder1/foldera should exist")
            self.assertTrue((self.watch_dir / "folderB" / "folder1" / "dat01.dat").exists(),
                          "dat file in folderB/folder1 should exist")
            self.assertTrue((self.watch_dir / "folderC" / "dat01.dat").exists(),
                          "dat file in folderC should exist")
            
            # Verify other folders are removed
            self.assertFalse((self.watch_dir / "folderA" / "folder2").exists(),
                           "folderA/folder2 should be removed")
            self.assertFalse((self.watch_dir / "folderA" / "folder3").exists(),
                           "folderA/folder3 should be removed")
            self.assertFalse((self.watch_dir / "folderB" / "folder2").exists(),
                           "folderB/folder2 should be removed")
            self.assertFalse((self.watch_dir / "folderB" / "folder3").exists(),
                           "folderB/folder3 should be removed")

            watcher.stop()
            time.sleep(1)
            self.assertFalse(watcher._running, "Watcher should not be running")
            
        finally:
            shutil.rmtree(stress_dir)

if __name__ == '__main__':
    unittest.main()
