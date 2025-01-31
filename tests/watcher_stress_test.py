import logging
import threading
import time
from typing import List
import unittest
import tempfile
import shutil
import base64
import json
import yaml
import hashlib
from pathlib import Path
from collections import namedtuple
from unittest.mock import Mock
from fileai.watcher import Watcher
from fileai.api import GeminiAPI
from dataclasses import dataclass

UploadResponse = namedtuple('UploadResponse', ['uri'])

OUTPUT_FOLDERS = [
    "medical",
    "financial",
    "travel",
    "personal",
    "technical",
    "legal",
    "receipts",
    "misc",
]

def get_filename_and_folder_from_relative_path(relative_path):
    sha256_hash = hashlib.sha256(str(relative_path).encode()).hexdigest()
    filename_prefix = sha256_hash[:10]
    folder_index = int(sha256_hash, 16) % len(OUTPUT_FOLDERS)
    folder = OUTPUT_FOLDERS[folder_index]
    filename = f"{filename_prefix}_file"
    logging.info(f"get filename folder {folder}/{filename}")
    return filename, folder
    
@dataclass
class File:
    original_path: Path
    relative_path: Path
    def get_expected_output_folder(self):
        return get_filename_and_folder_from_relative_path(self.relative_path)

class WatcherStressTest(unittest.TestCase):
    # Test configuration constants
    CHUNK_SIZE = 1024 * 1024  # 1MB chunks for large file test
    NUM_CHUNKS = 5  # Number of chunks for large file test
    SETUP_WAIT = 1  # Time to wait for watchdog setup
    
    def _set_folders(self):
        self.temp_dir = tempfile.mkdtemp()
        self.watch_dir = Path(self.temp_dir) / "watch"
        self.output_dir = Path(self.temp_dir) / "output"
        self.watch_dir.mkdir()
        self.output_dir.mkdir()
    
    def setUp(self):
        self._set_folders()
        self.pdf_base64 = "JVBERi0xLjEKJcKlwrHDqwoKMSAwIG9iagogIDw8IC9UeXBlIC9DYXRhbG9nCiAgICAgL1BhZ2VzIDIgMCBSCiAgPj4KZW5kb2JqCgoyIDAgb2JqCiAgPDwgL1R5cGUgL1BhZ2VzCiAgICAgL0tpZHMgWzMgMCBSXQogICAgIC9Db3VudCAxCiAgICAgL01lZGlhQm94IFswIDAgMzAwIDE0NF0KICA+PgplbmRvYmoKCjMgMCBvYmoKICA8PCAgL1R5cGUgL1BhZ2UKICAgICAgL1BhcmVudCAyIDAgUgogICAgICAvUmVzb3VyY2VzCiAgICAgICA8PCAvRm9udAogICAgICAgICAgIDw8IC9GMQogICAgICAgICAgICAgICA8PCAvVHlwZSAvRm9udAogICAgICAgICAgICAgICAgICAvU3VidHlwZSAvVHlwZTEKICAgICAgICAgICAgICAgICAgL0Jhc2VGb250IC9UaW1lcy1Sb21hbgogICAgICAgICAgICAgICA+PgogICAgICAgICAgID4+CiAgICAgICA+PgogICAgICAvQ29udGVudHMgNCAwIFIKICA+PgplbmRvYmoKCjQgMCBvYmoKICA8PCAvTGVuZ3RoIDU1ID4+CnN0cmVhbQogIEJUCiAgICAvRjEgMTggVGYKICAgIDAgMCBUZAogICAgKEhlbGxvIFdvcmxkKSBUagogIEVUCmVuZHN0cmVhbQplbmRvYmoKCnhyZWYKMCA1CjAwMDAwMDAwMDAgNjU1MzUgZiAKMDAwMDAwMDAxOCAwMDAwMCBuIAowMDAwMDAwMDc3IDAwMDAwIG4gCjAwMDAwMDAxNzggMDAwMDAgbiAKMDAwMDAwMDQ1NyAwMDAwMCBuIAp0cmFpbGVyCiAgPDwgIC9Sb290IDEgMCBSCiAgICAgIC9TaXplIDUKICA+PgpzdGFydHhyZWYKNTY1CiUlRU9GCg=="
        self.png_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z/C/HgAGgwJ/lK3Q6wAAAABJRU5ErkJggg=="
        
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

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def wait_for_files_processed(self, timeout, poll_interval):
        """Wait for all files to be processed with timeout."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            remaining = self.watcher.event_handler.get_num_watched_files()
            if remaining == 0:
                return True
            time.sleep(poll_interval)
        return False

    def _create_test_file(self, path: Path):
        """Helper to create a test file with specific type."""
        suffix = path.suffix[1:]
        if suffix == 'png':
            data = base64.b64decode(self.png_base64)
        elif suffix == 'pdf':
            data = base64.b64decode(self.pdf_base64)
        elif suffix == 'dat':
            data = b"test data"
        else:
            raise ValueError(f"Unsupported file type: {suffix}")
        
        with open(path, "wb") as f:
            f.write(data)
        return path
    
    def _create_directory_structure(self, base_dir: Path, structure: dict):
        """Create directory structure from configuration."""
        self.input_files: List[File] = []
        self.folders_to_be_kept = set()
        
        def process_directory(current_path: Path, dir_structure: dict):
            if 'files' in dir_structure:
                for file_config in dir_structure['files']:
                    file_pattern = file_config['pattern']
                    count = file_config['count']
                    if '*' in file_pattern:
                        base, ext = file_pattern.split('*')
                        for i in range(1, count + 1):
                            file_path = current_path / f"{base}{i:0002d}{ext}"
                            file = File(original_path=file_path.resolve(), relative_path=file_path.relative_to(base_dir))
                            logging.info(file_path.relative_to(base_dir))
                            self.input_files.append(file)
                    else:
                        file_path = current_path / file_pattern
                        file = File(original_path=file_path.resolve(), relative_path=file_path.relative_to(base_dir))
                        self.input_files.append(file)
            if 'directories' in dir_structure:
                for name, content in dir_structure['directories'].items():
                    path = current_path / name
                    path.mkdir(exist_ok=True)
                    self.folders_to_be_kept.add(path)
                    process_directory(path, content)
        
        process_directory(base_dir, structure)

        for file in self.input_files:
            self._create_test_file(file.original_path)

    def test_watcher_stress_test(self):
        # Mock file categorization to provide unique and deterministic values
        def unique_categorization(options) -> tuple[str, str]:
            relative_file_path = Path(options.get("relative_file_path", ""))
            filename, folder = get_filename_and_folder_from_relative_path(relative_file_path)
            return filename, folder

        self.watcher = Watcher(self.watch_dir, self.output_dir, self.api)
        self.watcher.organizer.file_renamer.categorize_file = Mock(
            side_effect=unique_categorization
        )
        monitor_thread = threading.Thread(target=self.watcher.start_monitoring)
        monitor_thread.daemon = True
        monitor_thread.start()
        self.assertTrue(self.watcher._running, "Watcher should be running")

        """Test monitoring a complex folder structure with many files."""
        #fixture_path = Path(__file__).parent / 'fixtures' / 'stress_test_structure.yaml'
        fixture_path = Path(__file__).parent / "fixtures" / "simple_structure.yaml"
        with open(fixture_path, 'r') as f:
            stress_dir = Path(tempfile.mkdtemp())
            structure = yaml.safe_load(f)
            self._create_directory_structure(stress_dir, structure)
        try:
            for item in stress_dir.iterdir():
                shutil.copytree(item, self.watch_dir / item.name)
                
            time.sleep(self.SETUP_WAIT)    
            self.assertTrue(self.wait_for_files_processed(100, 0.5), "Timed out waiting for files to be processed")
                
            for file in self.input_files:          
                relative_path = file.relative_path
                logging.info(f'Retrieved rel path {relative_path}')
                filename, folder = file.get_expected_output_folder()
            
                if file.relative_path.suffix in ['.png', '.pdf']:
                    output_path = Path(self.output_dir / folder / filename).with_suffix(
                        file.relative_path.suffix
                    )
                    input_path = Path(self.watch_dir / relative_path)
                    self.assertTrue(
                        output_path.exists(),
                        f"Supported file should exist in output: {relative_path}: {Path(folder) / Path(filename)} ",
                    )
                    self.assertFalse(input_path.exists(), f'Supported file should not exist in inbox: {file}')
                if file.relative_path.suffix == ".dat":
                    self.assertFalse(
                        Path(self.output_dir / folder / filename).exists(),
                        f'Unsupported file should not exist in output: {file.relative_path}'
                    )
                    self.assertTrue(
                        file.relative_path.exists(),
                        f"Unsupported file should still exist in inbox: {file.relative_path}",
                    )

            # Verify directory cleanup
            for path in self.input_files:
                parent_dir = path.original_path.parent
                if parent_dir not in self.folders_to_be_kept:
                    self.assertFalse(
                        parent_dir.exists(),
                        f"Empty directory should be removed: {parent_dir}"
                    )
                    logging.info(f"Assertion passed: Empty directory should be removed: {parent_dir}")

                self.watcher.stop()
                time.sleep(self.SETUP_WAIT)
                self.assertFalse(self.watcher._running, "Watcher should not be running")
        finally:        
            shutil.rmtree(stress_dir)
        logging.info("Finished test_watcher_stress_test")
        self.assertTrue(True, "All tests completed")


    def test_watcher_large_file_creation(self):
        """Test watcher with large file created in chunks."""        
        file_path = self.watch_dir / "large_file.txt"
        chunk_size = 1024 * 1024  # 1MB chunks for large file test
        num_chunks = 5  # Number of chunks for large file test

        # Start watcher in a thread
        self.watcher = Watcher(self.watch_dir, self.output_dir, self.api)
        self.watcher.organizer.file_renamer.categorize_file = Mock(
            return_value=('file', 'personal')
        )
        monitor_thread = threading.Thread(target=self.watcher.start_monitoring)
        monitor_thread.daemon = True
        monitor_thread.start()
        self.assertTrue(self.watcher._running, "Watcher should be running")
        
        input_content = ''
        # Create large file in chunks
        with open(file_path, "wb") as f:
            for i in range(num_chunks):
                chunk = f"chunk {i}".encode() * (
                    chunk_size // len(f"chunk {i}".encode())
                )
                f.write(chunk)
                input_content += f"chunk {i}" * (
                    chunk_size // len(f"chunk {i}".encode())
                ) 
                time.sleep(2)  # Simulate writing in chunks

        # Wait for file to be processed
        self.assertTrue(
            self.wait_for_files_processed(20, 0.5),
            "Timed out waiting for large file to be processed",
        )

        # Get relative path
        filename, folder = ("file", "personal")
        output_file_path = Path(self.output_dir / folder / filename).with_suffix(".txt")
        self.assertTrue(
            output_file_path.exists(), "Large file should be in output directory"
        )
        self.assertFalse(
            file_path.exists(), "Large file should not be in watch directory"
        )

        # Assert content of input and output files are the same
        with open(output_file_path, "r") as output_file:
            output_content = output_file.read()
       
        self.assertEqual(
            input_content,
            output_content,
            "Input and output file contents should be the same",
        )

        self.watcher.stop()
        time.sleep(self.SETUP_WAIT)
        self.assertFalse(self.watcher._running, "Watcher should not be running")
        logging.info("Finished test_watcher_large_file_creation")
        
        
if __name__ == '__main__':
    unittest.main()
