import time
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler

from fileai.file_organizer import FileOrganizer


@dataclass
class FileState:
    path: Path
    last_modified: float
    size: int
    stable_count: int = 0


class FileEventHandler(FileSystemEventHandler):
    def __init__(self, watcher):
        self.watcher = watcher
        self.file_states: Dict[Path, List[FileState]] = {}
        self.num_seen_files = 0

    def on_created(self, event):
        path = Path(event.src_path)
        if event.is_directory:
            return
        try:
            stats = path.stat()
            self.file_states[path] = FileState(path=path, last_modified=stats.st_mtime, size=stats.st_size)
            self.num_seen_files += 1
            logging.debug(f"File created: {path}")
        except (FileNotFoundError, PermissionError) as e:
            logging.error(f"Error handling created file {path}: {e}")

    def on_modified(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        try:
            self.file_states[path] = FileState(path=path, last_modified=time.time(), size=path.stat().st_size)
            logging.debug(f"File modified: {path}")
        except (FileNotFoundError, PermissionError) as e:
            logging.error(f"Error handling modified file {path}: {e}")

    def on_closed(self, event):
        """Handle file close events."""
        if event.is_directory:
            return

        path = Path(event.src_path)
        self._check_file_stability(path)
        
    def _get_stable_files(self):
        """Get files that haven't been modified for 3 seconds, sorted by directory depth."""
        current_time = time.time()
        stable_files = []
        for state in list(self.file_states.values()):
            if current_time - state.last_modified > 3:
                stable_files.append(state.path)
                self.file_states.pop(state.path)
        # Sort files by directory depth (process deeper files first)
        return sorted(stable_files, key=lambda p: len(p.parents), reverse=True)
    
    def get_num_watched_files(self):
        return len(self.file_states)
    
    def get_num_seen_files(self):
        return self.num_seen_files


class Watcher:
    """Base watcher class that handles file system monitoring."""

    def __init__(self, input_path, output_path, api):
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)

        self.organizer = FileOrganizer(self.input_path, self.output_path, api)
        self.event_handler = FileEventHandler(self)
        self.observer = PollingObserver(timeout=1)
        self.observer.schedule(self.event_handler, str(self.input_path), recursive=True)
        self._running = False

    def _should_process_file(self, file_path):
        """Check if a file should be processed."""
        path = Path(file_path)
        # Skip files in output directory or its subdirectories
        if self.output_path in path.parents or path == self.output_path:
            return False
        return True

    def _process_file(self, file_path):
        try:
            if self._should_process_file(file_path):
                self.organizer.organize_file(file_path)
        except Exception as e:
            logging.error(f"Failed to process {file_path}: {e}")

    def process_existing_files(self):
        self.organizer.organize_directory()

    def start_monitoring(self):
        self._running = True
        self.observer.start()
        try:
            while self._running:
                for path in self.event_handler._get_stable_files():
                    self._process_file(path)
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def start(self):
        self.process_existing_files()
        self.start_monitoring()

    def stop(self):
        self._running = False
        self.observer.stop()
        self.observer.join()
