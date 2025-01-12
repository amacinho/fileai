import logging
import threading
import time
import unittest
import tempfile
import shutil
import base64
import json
import yaml
from pathlib import Path
from collections import namedtuple
from unittest.mock import Mock
from fileai.watcher import Watcher
from fileai.api import GeminiAPI

UploadResponse = namedtuple('UploadResponse', ['uri'])

class WatcherTest(unittest.TestCase):
    # Test configuration constants
    WAIT_TIMEOUT = 300  # Maximum time to wait for file processing
    POLL_INTERVAL = 0.5  # Time between checks
    CHUNK_SIZE = 1024 * 1024  # 1MB chunks for large file test
    NUM_CHUNKS = 5  # Number of chunks for large file test
    SETUP_WAIT = 5  # Time to wait for watchdog setup
    
    def setUp(self):
        # Create temporary directories for testing
        self.folders = [
            "medical",
            "financial",
            "travel",
            "personal",
            "technical",
            "legal",
            "receipts",
            "misc",
        ]
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

    def wait_for_files_processed(self, watcher, timeout=None, poll_interval=None):
        """Wait for all files to be processed with timeout."""
        timeout = timeout or self.WAIT_TIMEOUT
        poll_interval = poll_interval or self.POLL_INTERVAL
        start_time = time.time()
        logging.debug(f"Waiting for files to be processed with timeout {timeout} and poll interval {poll_interval}")
        logging.debug(
            f"Files remaining: {watcher.event_handler.get_num_watched_files()}. Files seen: {watcher.event_handler.get_num_seen_files()}"
        )
        while time.time() - start_time < timeout:
            remaining = watcher.event_handler.get_num_watched_files()
            if remaining == 0:
                return True
            logging.debug(f"Files remaining: {remaining}. Files seen: {watcher.event_handler.get_num_seen_files()}")
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
    
    def unique_categorization(self, options) -> tuple[str, str]:
        source_file = Path(options.get("relative_file_path", ""))
        folder = self.folders[hash(source_file) % len(self.folders)]
        filename = f"file_{hash(source_file)}"
        return filename, folder

    def _create_directory_structure(self, base_dir: Path, structure: dict):
        """Create directory structure from configuration."""
        self.input_files = []
        self.folders_to_be_kept = set()
        
        def process_directory(current_path: Path, dir_structure: dict):
            if 'files' in dir_structure:
                for file_config in dir_structure['files']:
                    file_pattern = file_config['pattern']
                    count = file_config['count']
                    if '*' in file_pattern:
                        base, ext = file_pattern.split('*')
                        for i in range(1, count + 1):
                            file_path = current_path / f"{base}{i:02d}{ext}"
                            self.input_files.append(file_path)
                    else:
                        self.input_files.append(current_path / file_pattern)
            if 'directories' in dir_structure:
                for name, content in dir_structure['directories'].items():
                    path = current_path / name
                    path.mkdir(exist_ok=True)
                    self.folders_to_be_kept.add(path)
                    process_directory(path, content)
        
        process_directory(base_dir, structure)
        
        # Create all files
        for file in self.input_files:
            self._create_test_file(file)

    def test_watcher_stress_test(self):
        """Test monitoring a complex folder structure with many files."""
        # Load test structure from YAML fixture
        fixture_path = Path(__file__).parent / 'fixtures' / 'stress_test_structure.yaml'
        with open(fixture_path, 'r') as f:
            structure = yaml.safe_load(f)
            
        stress_dir = Path(tempfile.mkdtemp())
        try:
            # Create directory structure from configuration
            self._create_directory_structure(stress_dir, structure)
            
            # Create a new watcher instance with unique hash mock
            watcher = Watcher(self.watch_dir, self.output_dir, self.api)
            watcher.organizer.file_renamer.categorize_file = Mock(side_effect=self.unique_categorization)
            
            # Start monitoring in a thread
            monitor_thread = threading.Thread(target=watcher.start_monitoring)
            monitor_thread.daemon = True
            monitor_thread.start()
            time.sleep(self.SETUP_WAIT)
            
            self.assertTrue(watcher._running, "Watcher should be running")

            logging.info("Copying files to watch directory...")
            for item in stress_dir.iterdir():
                shutil.copytree(item, self.watch_dir / item.name)
            
            time.sleep(self.SETUP_WAIT)    
            # Wait for all files to be processed with timeout
            self.assertTrue(
                self.wait_for_files_processed(watcher),
                "Timed out waiting for files to be processed"
            )
            
            # Verify file processing
            for file in self.input_files:
                resolved_file_path = file.resolve()            
                relative_file_path = resolved_file_path.relative_to(stress_dir)
                filename, folder = self.unique_categorization(
                    {"relative_file_path": relative_file_path}
                )
                if file.suffix in ['.png', '.pdf']:
                    # Add suffix to the filename path
                    output_path = Path(self.output_dir / folder / filename).with_suffix(file.suffix)
                    input_path = Path(self.watch_dir / relative_file_path)
                    self.assertTrue(
                        output_path.exists(),
                        f"Supported file should exist in output: {file}: {output_path} ",
                    )
                    self.assertFalse(input_path.exists(), f'Supported file should not exist in inbox: {file}')
                if file.suffix == '.dat':
                    self.assertFalse(
                        Path(self.output_dir / folder / filename).exists(),
                        f'Unsupported file should not exist in output: {file}'
                    )
                    self.assertTrue(file.exists(), f'Unsupported file should still exist in inbox: {file}')
 
            # Verify directory cleanup
            for path in self.input_files:
                parent_dir = path.parent
                if parent_dir not in self.folders_to_be_kept:
                    self.assertFalse(
                        parent_dir.exists(),
                        f"Empty directory should be removed: {parent_dir}"
                    )

            watcher.stop()
            time.sleep(self.SETUP_WAIT)
            self.assertFalse(watcher._running, "Watcher should not be running")
            
        finally:
            shutil.rmtree(stress_dir)

if __name__ == '__main__':
    unittest.main()
