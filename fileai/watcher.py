import time
import logging
from pathlib import Path
from queue import Queue
from dataclasses import dataclass
from typing import Dict
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from fileai.file_organizer import FileOrganizer

@dataclass
class FileState:
    """Tracks the state of a file being watched."""
    path: Path
    last_modified: float
    size: int
    stable_count: int = 0

class FileEventHandler(FileSystemEventHandler):
    """Handles file system events and tracks file modifications."""
    
    def __init__(self, watcher):
        self.watcher = watcher
        self.file_states: Dict[Path, FileState] = {}
        self.directory_ready: Dict[Path, bool] = {
            self.watcher.input_path: True  # Input directory is always ready
        }
        self.pending_files: Dict[Path, FileState] = {}  # Files waiting for directory readiness
        
    def on_created(self, event):
        """Handle file creation events."""
        path = Path(event.src_path)
        
        if event.is_directory:
            # Mark directory and all parent directories as ready for monitoring
            self._mark_directory_ready(path)
            
            # Check if any pending files can now be processed
            self._process_pending_files()
            return
            
        # Only process file if its parent directory is ready
        if not self._is_directory_ready(path.parent):
            logging.debug(f"Queueing file for later processing: {path}")
            try:
                stats = path.stat()
                self.pending_files[path] = FileState(
                    path=path,
                    last_modified=stats.st_mtime,
                    size=stats.st_size
                )
            except (FileNotFoundError, PermissionError):
                pass
            return
            
        logging.debug(f"Processing file in ready directory: {path}")
            
        try:
            stats = path.stat()
            self.file_states[path] = FileState(
                path=path,
                last_modified=stats.st_mtime,
                size=stats.st_size
            )
            # Try to process immediately in case it's a small file
            self._check_file_stability(path)
        except (FileNotFoundError, PermissionError):
            pass

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
            
        path = Path(event.src_path)
        self._check_file_stability(path)

    def _check_file_stability(self, path):
        """Check if a file is stable and ready for processing."""
        try:
            stats = path.stat()
            
            if path in self.file_states:
                state = self.file_states[path]
                # If file hasn't changed in size/mtime, increment stable count
                if (stats.st_size == state.size and 
                    stats.st_mtime == state.last_modified):
                    state.stable_count += 1
                    # File appears stable after 2 checks
                    if state.stable_count >= 2:
                        self.watcher._process_file(path)
                        del self.file_states[path]
                else:
                    # File still changing, update state
                    state.size = stats.st_size
                    state.last_modified = stats.st_mtime
                    state.stable_count = 0
            else:
                # New file we haven't seen before
                self.file_states[path] = FileState(
                    path=path,
                    last_modified=stats.st_mtime,
                    size=stats.st_size
                )
        except (FileNotFoundError, PermissionError):
            if path in self.file_states:
                del self.file_states[path]

    def _mark_directory_ready(self, directory: Path) -> None:
        """Mark a directory and all its parents as ready for monitoring."""
        current = directory
        while current != self.watcher.input_path:
            if not self.directory_ready.get(current, False):
                self.directory_ready[current] = True
                logging.debug(f"Directory marked ready: {current}")
            current = current.parent

    def _process_pending_files(self) -> None:
        """Process any pending files whose directories are now ready."""
        for path, state in list(self.pending_files.items()):
            if self._is_directory_ready(path.parent):
                logging.debug(f"Processing previously pending file: {path}")
                self.file_states[path] = state
                del self.pending_files[path]
                self._check_file_stability(path)

    def _is_directory_ready(self, directory: Path) -> bool:
        """Check if a directory and all its parents are ready for monitoring."""
        current = directory
        while current != self.watcher.input_path:
            if not self.directory_ready.get(current, False):
                return False
            current = current.parent
        return True

    def on_closed(self, event):
        """Handle file close events."""
        if event.is_directory:
            return
            
        path = Path(event.src_path)
        self._check_file_stability(path)

class Watcher:
    """Monitors a directory for file changes and processes stable files."""
    
    def __init__(self, input_path, output_path, api):
        """Initialize the watcher.
        
        Args:
            input_path: Path to watch for new files
            output_path: Path to output processed files
            api: API instance for processing files
        """
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        
        # Initialize components
        self.organizer = FileOrganizer(self.input_path, self.output_path, api)
        self.event_handler = FileEventHandler(self)
        self.observer = Observer()
        self.observer.schedule(
            self.event_handler,
            str(self.input_path),
            recursive=True
        )
        self._running = False
        
        # Queue for tracking file modifications
        self.file_queue = Queue()
        
    def _should_process_file(self, file_path):
        """Check if a file should be processed."""
        path = Path(file_path)
        # Skip files in output directory or its subdirectories
        if self.output_path in path.parents or path == self.output_path:
            return False
        return True

    def _process_file(self, file_path):
        """Process a file and update modification queue."""
        try:
            if self._should_process_file(file_path):
                # Add file state to queue before processing
                try:
                    stats = Path(file_path).stat()
                    self.file_queue.put({
                        'path': str(file_path),
                        'last_modified': stats.st_mtime,
                        'size': stats.st_size
                    })
                except (FileNotFoundError, PermissionError):
                    pass
                    
                # Process the file
                self.organizer.organize_file(file_path)
                logging.info(f"Successfully processed {file_path}")
        except Exception as e:
            logging.error(f"Failed to process {file_path}: {e}")

    def process_existing_files(self):
        """Process any existing files in the input directory."""
        logging.info(f"Processing existing files in {self.input_path}...")
        # Track files before processing
        for path in self.input_path.rglob('*'):
            if path.is_file() and self._should_process_file(path):
                try:
                    stats = path.stat()
                    self.file_queue.put({
                        'path': str(path),
                        'last_modified': stats.st_mtime,
                        'size': stats.st_size
                    })
                except (FileNotFoundError, PermissionError):
                    pass
        
        self.organizer.organize_directory()
        
    def start_monitoring(self):
        """Start monitoring for new files."""
        logging.info(f"Monitoring {self.input_path} for new files...")
        self._running = True
        self.observer.start()
        
        try:
            while self._running:
                # Check all files in watch states and pending files periodically
                for path in list(self.event_handler.file_states.keys()):
                    self.event_handler._check_file_stability(path)
                self.event_handler._process_pending_files()  # Retry pending files periodically
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
        
    def start(self):
        """Start monitoring the input directory."""
        # First process any existing files
        self.process_existing_files()
        
        # Then start watching for new files
        self.start_monitoring()
        
    def stop(self):
        """Stop monitoring the input directory."""
        self._running = False
        self.observer.stop()
        self.observer.join()
