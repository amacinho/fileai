import logging
import os
import random
import shutil
import string
import threading
import time
from pathlib import Path
from unittest.mock import Mock

import pytest

from fileai.file_operator import FileOperator
from fileai.pipeline import DocumentPipeline
from fileai.watcher import Watcher

# Test configuration
OUTPUT_FOLDERS = ["medical", "financial", "travel", "personal", "technical", "legal", "receipts", "misc"]
CHUNK_SIZE = 1024 * 1024  # 1MB chunks for large file test
NUM_CHUNKS = 5  # Number of chunks for large file test
SETUP_WAIT = 5  # Time to wait for watchdog setup

@pytest.fixture
def temp_dirs(tmp_path):
    """Create temporary directories for testing."""
    watch_dir = tmp_path / "watch"
    output_dir = tmp_path / "output"
    watch_dir.mkdir()
    output_dir.mkdir()
    logging.info(f"Created temporary directories: {watch_dir}, {output_dir}")
    yield watch_dir, output_dir
    shutil.rmtree(tmp_path)

file_categories = {}

def get_categorization(path):
    """Get consistent categorization for a file."""
    logging.debug(f"Getting categorization for {path}")
    if path not in file_categories:
        # Create consistent but varied folder assignment using path hash
        path_hash = hash(str(path))
        folder_index = abs(path_hash) % len(OUTPUT_FOLDERS)
        
        file_categories[path] = {
            "filename": f"file_{abs(path_hash) % 1000000}",  # Deterministic filename
            "folder": OUTPUT_FOLDERS[folder_index],  # Spread across folders
            "doc_type": "invoice",
            "doc_date": "2016-01-01",
            "doc_topic": "test",
            "doc_owner": "test",
            "doc_keywords": ["test"],
        }
    logging.debug(f"Categorized {path} as {file_categories[path]}")
    return file_categories[path]["filename"], file_categories[path]["folder"]


@pytest.fixture
def watcher_setup(temp_dirs):
    """Set up and start a watcher for testing."""
    watch_dir, output_dir = temp_dirs
    
    file_operator = FileOperator(
        input_base_path=watch_dir,
        output_base_path=output_dir,
        remove_input_files=True
    )
    
    # Create a simple mock for the API
    mock_api = Mock()
    mock_api.rate_limiter = Mock()
    mock_api.rate_limiter.max_calls = 1000
    
    watcher = Watcher(watch_dir, output_dir, mock_api)
    
    # Create a mock categorizer that uses our file_categories
    mock_categorizer = Mock()
    mock_categorizer.categorize_document = Mock(
        side_effect=lambda path: get_categorization(path)
    )
    
    watcher.pipeline = DocumentPipeline(
        categorizer=mock_categorizer,
        file_operator=file_operator
    )
    
    # Start watcher in a separate thread
    monitor_thread = threading.Thread(target=watcher.start_monitoring)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # Wait for watcher to start
    time.sleep(SETUP_WAIT)
    
    yield watcher, watch_dir, output_dir, file_categories
    
    # Cleanup
    watcher.stop()
    time.sleep(SETUP_WAIT)

def create_test_file(path: Path):
    """Helper to create a test file with specific type."""
    # Create a 1000-length random character data
    data = ''.join(random.choices(string.ascii_letters + string.digits, k=1000)).encode('utf-8')
    
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    logging.debug(f"Created test file: {path}")
    return path

@pytest.fixture
def temp_input_dir(tmp_path):
    """Create a temporary input directory with test folder structure."""
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    
    # Create test files in the input directory
    for i in range(1000):
        create_test_file(input_dir / f"test_file_{i}.txt")
    yield input_dir
    shutil.rmtree(input_dir)

def wait_for_files_processed(watcher, timeout=200, poll_interval=0.5):
    """Wait for all files to be processed with timeout."""
    start_time = time.time()
    is_init = False
    while time.time() - start_time < timeout:
        remaining = watcher.event_handler.get_num_watched_files()
        if remaining == 0 and is_init:
            return True
        if remaining > 0:
            is_init = True
        time.sleep(poll_interval)
    return False


def test_high_load(watcher_setup, temp_input_dir):
    """Test monitoring a complex folder structure with many files."""
    watcher, watch_dir, output_dir, _ = watcher_setup
    
    # Copy test files in temp_input_dir to watch directory
    
    shutil.copytree(temp_input_dir, watch_dir / 'files')
    
    # Wait for files to be processed
    assert wait_for_files_processed(watcher), "Timed out waiting for files to be processed"
    
    # Print contents of watch directory recursively
    logging.info(f"Watch directory contents: {list(watch_dir.rglob('*'))}")
    # watch directory should be empty
    assert len(list(watch_dir.iterdir())) == 0, "Watch directory is not empty"
            
    # Recursively print output folder
    logging.info(f"Output directory contents: {list(output_dir.rglob('*'))}")

    # Count files in the output folder recursively, do not count folders
    output_files = [f for f in list(output_dir.rglob('*')) if f.is_file()]
    processed_count = len(output_files)
    logging.info(f"Processed {processed_count} files")

    # Verify all files were processed
    assert processed_count == len(input_files), "Not all files were processed"

def test_large_file_handling(watcher_setup):
    """Test watcher's ability to handle large files being written in chunks."""
    watcher, watch_dir, output_dir, file_categories = watcher_setup
    
    # Create large file in chunks
    test_file = watch_dir / "large_file.txt"
    input_content = ''
    
    with open(test_file, "wb") as f:
        for i in range(NUM_CHUNKS):
            chunk = f"chunk {i}".encode() * (CHUNK_SIZE // len(f"chunk {i}".encode()))
            f.write(chunk)
            f.flush()  # Force buffer flush
            os.fsync(f.fileno())  # Force OS write
            input_content += f"chunk {i}" * (CHUNK_SIZE // len(f"chunk {i}".encode()))
            time.sleep(0.5)  # Simulate writing in chunks
    
    # Wait for file to be processed
    assert wait_for_files_processed(watcher, 20, 0.5), "Timed out waiting for large file to be processed"
    
    # Verify file was processed correctly
    assert not test_file.exists(), "Large file should not be in watch directory"
    
    # Find the processed file in output directory
    processed_file = None
    for folder in OUTPUT_FOLDERS:
        folder_path = output_dir / folder
        if folder_path.exists():
            for file_path in folder_path.glob("*.txt"):
                # Verify content to confirm it's our file
                with open(file_path, "r") as output_file:
                    output_content = output_file.read()
                    if input_content == output_content:
                        processed_file = file_path
                        break
            if processed_file:
                break
    
    assert processed_file is not None, "Processed file not found in any output folder"
    logging.info(f"Found processed file at {processed_file}")
    
    # Verify content matches
    with open(processed_file, "r") as output_file:
        output_content = output_file.read()
    
    assert input_content == output_content, "Input and output file contents should be the same"
