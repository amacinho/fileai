import logging
from pathlib import Path
from typing import Dict

from fileai.pipeline import DocumentPipeline
from fileai.file_system_operator import FileSystemOperator

class Processor:
    """Base Processor class that executes the document processing pipeline."""

    def __init__(self, input_path, output_path, api):
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        self.processed_files: Dict[str, int] = {}

        self.file_system_operator = FileSystemOperator(
            input_base_path=self.input_path,
            output_base_path=self.output_path,
            remove_input_files=True
        )
        
        self.pipeline = DocumentPipeline(
            categorizer=api,
            file_system_operator=self.file_system_operator
        )
        
        # Scan output directory and build hash dictionary
        self.file_system_operator.scan_output_directory()
        
        # Print duplicate stats
        self.print_duplicate_stats()
        
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
        if ext not in self.processed_files:
            self.processed_files[ext] = 0
        self.processed_files[ext] += 1
              
    def process_existing_files(self):
        """Process any existing files in the input directory"""
        for file_path in self.input_path.rglob('*'):
            if not self._should_process_file(file_path):
                continue
            try:           
                target_path = self.pipeline.process(file_path)
                self.track_extension(file_path)      
            except Exception as e:
                logging.error(f"[Processor] Failed to process {file_path}: {e}")
                # Move failed file to unsupported
                self.file_system_operator.move_to_unsupported(file_path)
            else:
                logging.debug(f"[Processor] Processed existing file: {file_path} -> {target_path}")

    def print_duplicate_stats(self):
        """Print statistics about duplicate files."""
        stats = self.file_system_operator.get_duplicate_stats()
        
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
            for file_hash, paths in self.file_system_operator.file_hash_dict.items():
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
    
