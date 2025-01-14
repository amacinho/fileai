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
        self.processed_files: Dict[str, int] = {}

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
        """Get files that haven't been modified for 5 seconds. Order by folder depth."""
        current_time = time.time()
        stable_files = {}
        for path,state in self.file_states.items():
            if current_time - state.last_modified > 5:
                stable_files[path] = state
        logging.debug(f"Found {len(stable_files)} stable files")
        return sorted(stable_files.keys(), key=lambda x: len(x.parts))
    
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
                ext = Path(file_path).suffix
                if ext not in self.event_handler.processed_files:
                    self.event_handler.processed_files[ext] = 0
                self.event_handler.processed_files[ext] += 1
        except Exception as e:
            logging.error(f"Failed to process {file_path}: {e}")

    def process_existing_files(self):
        self.organizer.organize_directory()

    def start_monitoring(self):
        self._running = True
        self.observer.start()
        try:
            while self._running:
                stable_files = self.event_handler._get_stable_files()
                for path in stable_files:
                    self._process_file(path)
                    self.event_handler.file_states.pop(path)
                logging.info(f"Observed {self.event_handler.get_num_seen_files()} files, processed {len(stable_files)}, {self.event_handler.get_num_watched_files()} remaining, processed by extension: {self.event_handler.processed_files}")
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
