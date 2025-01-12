import argparse
from fileai.api import GeminiAPI
from fileai.watcher import Watcher
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
    watcher = Watcher(args.input_path, args.output_path, api)

    if args.monitor:
        try:
            # First process existing files
            watcher.process_existing_files()
            
            # Then start monitoring for new files
            watcher.start_monitoring()
        except KeyboardInterrupt:
            watcher.stop()
    else:
        # Just process existing files without monitoring
        watcher.process_existing_files()

if __name__ == "__main__":
    main()
