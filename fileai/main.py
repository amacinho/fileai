import argparse
import time
from pathlib import Path
import logging
from watchdog.observers import Observer
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


class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, organizer, output_path):
        self.organizer = organizer
        self.output_path = Path(output_path)

    def on_created(self, event):
        if not event.is_directory:
            file_path = Path(event.src_path)
            if not self.is_output_file(file_path):
                self.organizer.organize_file(file_path)

    def is_output_file(self, file_path):
        try:
            return self.output_path in file_path.parents
        except:
            return False


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
    organizer = FileOrganizer(Path(args.input_path), Path(args.output_path), api)

    event_handler = FileChangeHandler(organizer, args.output_path)
    # First process existing files
    organizer.organize_directory()

    # Then start watching for new files
    if args.monitor:
        logging.info(f"Monitoring {args.input_path} for new files...")
        observer = Observer()
        observer.schedule(event_handler, args.input_path, recursive=True)
        observer.start()
        try:
            # Keep the main thread alive while the observer runs
            while observer.is_alive():
                observer.join(1)  # Wait for the observer thread, but allow KeyboardInterrupt
        except KeyboardInterrupt:
            observer.stop()
        observer.join()


if __name__ == "__main__":
    main()
