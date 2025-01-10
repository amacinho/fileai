import argparse
import os
from pathlib import Path
import logging
import time
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler
from fileai.api import GeminiAPI
from fileai.file_organizer import FileOrganizer
from fileai.config import get_config_file

def create_api(api_type: str, api_key: str = None, model: str = None):
    """Create the appropriate API instance based on type.

    Args:
        api_type (str): Type of API to use (e.g., 'gemini')
        api_key (str, optional): API key to use. If not provided, will try to load from config.
        model (str, optional): Model name to use. If not provided, will try to load from config.
    """
    if api_type == "gemini":
        return GeminiAPI(api_key=api_key, model=model)
    else:
        raise ValueError(f"Unsupported API type: {api_type}")

class FileStabilityHandler(FileSystemEventHandler):
    def __init__(self, organizer, output_path, max_retries=3, stability_timeout=300):
        """Initialize the handler with configurable stability parameters.
        
        Args:
            organizer: FileOrganizer instance to process stable files
            output_path: Path to output directory
            max_retries: Maximum number of processing attempts (default: 3)
            stability_timeout: Maximum time in seconds to wait for stability (default: 300)
        """
        self.organizer = organizer
        self.output_path = Path(output_path)
        self.max_retries = max_retries
        self.stability_timeout = stability_timeout
        
        # Track file states with more metadata
        self.tracked_files = {}  # {path: {size: int, last_modified: float, stable_count: int, retries: int, first_seen: float}}
        self.stable_files = set()  # Successfully processed files
        self.last_check = time.time()

    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory:
            file_path = Path(event.src_path)
            if not self.is_output_file(file_path):
                try:
                    current_time = time.time()
                    self.tracked_files[str(file_path)] = {
                        'size': os.path.getsize(file_path),
                        'last_modified': os.path.getmtime(file_path),
                        'stable_count': 0,
                        'retries': 0,
                        'first_seen': current_time
                    }
                    logging.debug(f"Started tracking new file: {file_path}")
                except (FileNotFoundError, OSError) as e:
                    logging.debug(f"Could not start tracking {file_path}: {e}")

    def dispatch(self, event):
        """Override dispatch to periodically check file stability."""
        super().dispatch(event)
        
        # Check stability every second
        current_time = time.time()
        if current_time - self.last_check >= 1.0:
            self.check_file_stability()
            self.last_check = current_time

    def check_file_stability(self):
        """Check stability of tracked files and process them when ready."""
        current_time = time.time()
        files_to_remove = []

        for file_path, metadata in list(self.tracked_files.items()):
            if file_path in self.stable_files:
                files_to_remove.append(file_path)
                continue

            try:
                current_size = os.path.getsize(file_path)
                current_mtime = os.path.getmtime(file_path)
                
                # Check if file has timed out
                if current_time - metadata['first_seen'] > self.stability_timeout:
                    logging.warning(f"File {file_path} stability timeout exceeded")
                    files_to_remove.append(file_path)
                    continue

                # Check if file is being modified
                if current_mtime > metadata['last_modified']:
                    metadata.update({
                        'size': current_size,
                        'last_modified': current_mtime,
                        'stable_count': 0
                    })
                    continue

                # Check if size is stable
                if current_size == metadata['size']:
                    metadata['stable_count'] += 1
                    # Consider file stable after 2 consecutive checks
                    if metadata['stable_count'] >= 2:
                        self._process_stable_file(file_path, metadata)
                        if file_path in self.stable_files:
                            files_to_remove.append(file_path)
                else:
                    metadata.update({
                        'size': current_size,
                        'last_modified': current_mtime,
                        'stable_count': 0
                    })

            except FileNotFoundError:
                files_to_remove.append(file_path)
            except Exception as e:
                logging.error(f"Error checking stability for {file_path}: {e}")

        # Clean up processed or deleted files
        for file_path in files_to_remove:
            self.tracked_files.pop(file_path, None)

    def _process_stable_file(self, file_path, metadata):
        """Process a file that appears to be stable."""
        try:
            if metadata['retries'] >= self.max_retries:
                self.stable_files.add(file_path)  # Mark as done to stop retrying
                return

            self.organizer.organize_file(file_path)
            self.stable_files.add(file_path)

        except Exception as e:
            metadata['retries'] += 1
            logging.warning(f"Failed to process {file_path} (attempt {metadata['retries']}): {e}")
            # File will be retried on next stability check if retries < max_retries

    def is_output_file(self, file_path):
        """Check if a file is in the output directory."""
        return self.output_path in file_path.parents

class Monitor:
    """Monitors a directory for file changes and processes stable files."""
    
    def __init__(self, input_path, output_path, api, poll_interval=1.0):
        """Initialize the monitor.
        
        Args:
            input_path: Path to watch for new files
            output_path: Path to output processed files
            api: API instance for processing files
            poll_interval: How often to check for file changes in seconds
        """
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        self.poll_interval = poll_interval
        
        # Initialize components
        self.organizer = FileOrganizer(self.input_path, self.output_path, api)
        self.handler = FileStabilityHandler(self.organizer, self.output_path)
        self.observer = PollingObserver(timeout=self.poll_interval)
        
    def start(self):
        """Start monitoring the input directory."""
        # First process any existing files
        self.organizer.organize_directory()
        
        # Then start watching for new files
        logging.info(f"Monitoring {self.input_path} for new files...")
        self.observer.schedule(self.handler, str(self.input_path), recursive=True)
        self.observer.start()
        
    def stop(self):
        """Stop monitoring the input directory."""
        self.observer.stop()
        self.observer.join()

def main():
    parser = argparse.ArgumentParser(description="Process files using various AI APIs.")
    parser.add_argument(
        "input_path",
        help="Path to input folder. All content under this folder will be processed recursively.",
    )
    parser.add_argument("output_path", help="Path to output folder")
    parser.add_argument(
        "api_type", choices=["gemini"], type=str.lower, help="LLM service to use"
    )
    parser.add_argument(
        "--monitor",
        action="store_true",
        help="Monitor the input folder for new files and process them in real-time. Monitoring starts after processing existing files. (optional, defaults to no monitoring)")

    parser.add_argument(
        "--api-key",
        help=f"API key (optional, can also be set via config file {get_config_file})",
    )
    parser.add_argument(
        "--model", help="Model name (optional, defaults to gemini-2.0-flash-exp)"
    )
    args = parser.parse_args()

    api = create_api(args.api_type, api_key=args.api_key, model=args.model)
    monitor = Monitor(args.input_path, args.output_path, api)

    if args.monitor:
        try:
            monitor.start()
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            monitor.stop()
    else:
        # Just process existing files without monitoring
        monitor.organizer.organize_directory()

if __name__ == "__main__":
    main()
