import argparse
import os
from pathlib import Path
import logging
import inotify.adapters

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

class Monitor:
    """Monitors a directory for file changes and processes stable files."""
    
    def __init__(self, input_path, output_path, api):
        """Initialize the monitor.
        
        Args:
            input_path: Path to watch for new files
            output_path: Path to output processed files
            api: API instance for processing files
        """
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        
        # Initialize components
        self.organizer = FileOrganizer(self.input_path, self.output_path, api)
        self.inotify = inotify.adapters.InotifyTree(str(self.input_path))
        self._running = False
        
    def _should_process_file(self, file_path):
        """Check if a file should be processed."""
        path = Path(file_path)
        # Skip files in output directory or its subdirectories
        if self.output_path in path.parents or path == self.output_path:
            return False
        return True

    def _process_file(self, file_path):
        """Process a file."""
        try:
            if self._should_process_file(file_path):
                self.organizer.organize_file(file_path)
                logging.info(f"Successfully processed {file_path}")
        except Exception as e:
            logging.error(f"Failed to process {file_path}: {e}")

    def _handle_events(self):
        """Handle inotify events."""
        for event in self.inotify.event_gen(yield_nones=False):
            if not self._running:
                break

            (_, type_names, path, filename) = event
            
            if not filename:  # Directory event
                continue
                
            # Only process files when they're completely written
            logging.debug(f"Received event: {type_names} on {filename}")
            if 'IN_CLOSE_WRITE' in type_names:
                file_path = Path(os.path.join(path, filename))
                self._process_file(file_path)

    def process_existing_files(self):
        """Process any existing files in the input directory."""
        logging.info(f"Processing existing files in {self.input_path}...")
        self.organizer.organize_directory()
        
    def start_monitoring(self):
        """Start monitoring for new files."""
        logging.info(f"Monitoring {self.input_path} for new files...")
        self._running = True
        self._handle_events()
        
    def start(self):
        """Start monitoring the input directory."""
        # First process any existing files
        self.process_existing_files()
        
        # Then start watching for new files
        self.start_monitoring()
        
    def stop(self):
        """Stop monitoring the input directory."""
        self._running = False

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
            # First process existing files
            monitor.process_existing_files()
            
            # Then start monitoring for new files
            monitor.start_monitoring()
        except KeyboardInterrupt:
            monitor.stop()
    else:
        # Just process existing files without monitoring
        monitor.process_existing_files()

if __name__ == "__main__":
    main()
