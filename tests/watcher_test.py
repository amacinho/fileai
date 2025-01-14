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

    
class WatcherTest(unittest.TestCase):
    
    
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


    

if __name__ == '__main__':
    unittest.main()
