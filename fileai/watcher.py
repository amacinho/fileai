import time
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler

from fileai.pipeline import DocumentPipeline
from fileai.file_operator import FileOperator


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
        except (FileNotFoundError, PermissionError) as e:
            logging.error(f"Error handling created file {path}: {e}")

    def on_modified(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        try:
            self.file_states[path] = FileState(path=path, last_modified=time.time(), size=path.stat().st_size)
            #logging.debug(f"File modified: {path}")
        except (FileNotFoundError, PermissionError) as e:
            logging.error(f"Error handling modified file {path}: {e}")

        
    def _get_stable_files(self):
        """Get files that haven't been modified for 5 seconds. Order by folder depth."""
        current_time = time.time()
        stable_files = [
            path for path, state in self.file_states.items()
            if current_time - state.last_modified > 5
        ]
        logging.debug(f"[Watcher] Found {len(stable_files)} stable files and {len(self.file_states) - len(stable_files)} unstable files")
        return sorted(stable_files, key=lambda x: len(x.parts))
    
    def get_num_watched_files(self):
        return len(self.file_states)
    
    def get_num_seen_files(self):
        return self.num_seen_files


class Watcher:
    """Base watcher class that handles file system monitoring."""

    def __init__(self, input_path, output_path, api):
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)

        self.file_operator = FileOperator(
            input_base_path=self.input_path,
            output_base_path=self.output_path,
            remove_input_files=True
        )
        
        self.pipeline = DocumentPipeline(
            categorizer=api,
            file_operator=self.file_operator
        )
        
        # Scan output directory and build hash dictionary
        self.file_operator.scan_output_directory()
        
        # Print duplicate stats
        self.print_duplicate_stats()
        
        self.event_handler = FileEventHandler(self)
        self.observer = PollingObserver(timeout=1)
        self.observer.schedule(self.event_handler, str(self.input_path), recursive=True)
        self._running = False

    def _should_process_file(self, file_path):
        """Check if a file should be processed."""
        path = Path(file_path)
        # Skip folders, files in output directory or its subdirectories
        if (not file_path.is_file()) or self.output_path in path.parents or path == self.output_path:
            return False
        return True

    def track_extension(self, file_path):
        """Track the extension of the processed file."""
        ext = Path(file_path).suffix
        if ext not in self.event_handler.processed_files:
            self.event_handler.processed_files[ext] = 0
        self.event_handler.processed_files[ext] += 1
              
    def process_existing_files(self):
        """Process any existing files in the input directory"""
        for file_path in self.input_path.rglob('*'):
            if not self._should_process_file(file_path):
                continue
            try:           
                target_path = self.pipeline.process(file_path)
                self.track_extension(file_path)      
            except Exception as e:
                logging.error(f"[Watcher] Failed to process {file_path}: {e}")
                # Move failed file to unsupported
                self.file_operator.move_to_unsupported(file_path)
            else:
                logging.debug(f"[Watcher] Processed existing file: {file_path} -> {target_path}")

    def start_monitoring(self):
        self._running = True
        self.observer.start()
        try:
            while self._running:
                stable_files = self.event_handler._get_stable_files()
                for path in list(stable_files):
                    try:
                        self.pipeline.process(path)
                        self.track_extension(path)
                    except Exception as e:
                        logging.error(f"[Watcher] Failed to process {path}: {e}")
                        # Move failed file to unsupported
                        self.file_operator.move_to_unsupported(path)
                    finally:
                        self.event_handler.file_states.pop(path)
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def start(self):
        self.process_existing_files()
        self.start_monitoring()

    def print_duplicate_stats(self):
        """Print statistics about duplicate files."""
        stats = self.file_operator.get_duplicate_stats()
        
        print("\nDuplicate File Statistics:")
        print(f"Total files scanned: {stats['total_files']}")
        print(f"Unique files: {stats['unique_files']}")
        print(f"Duplicate files: {stats['duplicate_files']}")
        print(f"Duplicate groups: {stats['duplicate_groups']}")
        
        def format_size(size_bytes):
            """Format file size in a human-readable format."""
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size_bytes < 1024 or unit == 'GB':
                    return f"{size_bytes:.2f} {unit}"
                size_bytes /= 1024
        
        if stats['duplicate_groups'] > 0:
            print("\nDuplicate groups:")
            for file_hash, paths in self.file_operator.file_hash_dict.items():
                if len(paths) > 1:
                    # Get size of first file
                    size = paths[0].stat().st_size
                    formatted_size = format_size(size)
                    print(f"- {paths[0]} ({len(paths)} duplicates, {formatted_size})")
                    # Print all duplicate files with indentation
                    for path in paths[1:]:
                        size = path.stat().st_size
                        formatted_size = format_size(size)
                        print(f"    - {path} ({formatted_size})")
    
    def stop(self):
        self._running = False
        self.observer.stop()
        self.observer.join()
