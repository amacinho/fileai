import logging
from pathlib import Path
from typing import Optional, Tuple

from fileai.directory_manager import DirectoryManager
from fileai.pipeline import DocumentPipeline
from fileai import document_handlers

class DocumentProcessor:
    """Orchestrates the document processing workflow"""

    def __init__(self, input_dir: Path, output_dir: Path, api):
        self.input_dir = input_dir.resolve()
        self.output_dir = output_dir.resolve()
        self.dir_manager = DirectoryManager(output_dir)
        self.api = api
        
        # Initialize directory structure
        self.dir_manager.ensure_category_structure()

    def process_document(self, file_path: Path) -> Optional[Path]:
        """
        Process a single document through the complete workflow.
        Returns the new file path if successful, None otherwise.
        """
        if not self._validate_document(file_path):
            return None

        pipeline = DocumentPipeline(file_path)
        final_path = pipeline.process(self.api, self.output_dir)
        
        if pipeline.success:
            # Get relative paths for logging
            try:
                input_relative = str(file_path.relative_to(self.input_dir))
                output_relative = str(final_path.relative_to(self.output_dir))
                logging.info(f"Processed: {input_relative} -> {output_relative}")
            except ValueError:
                logging.info(f"Processed: {file_path} -> {final_path}")
            
            # Cleanup empty directories
            self.dir_manager.cleanup_empty_dirs(file_path.parent, self.input_dir)
            
        return final_path

    def process_directory(self) -> None:
        """Process all files in the input directory."""
        try:
            # Get all files and sort by directory depth (process deeper files first)
            files = sorted(
                self.input_dir.rglob("*"),
                key=lambda p: len(p.parents),
                reverse=True
            )
            
            for file_path in files:
                if not file_path.is_file() or file_path.is_relative_to(self.output_dir):
                    continue
                    
                self.process_document(file_path)
                
        except Exception as e:
            logging.error(f"Error processing directory: {e}")
            raise

    def _validate_document(self, file_path: Path) -> bool:
        """Check if a document can be processed."""
        if file_path.name == ".DS_Store":
            return False
            
        handler = document_handlers.get_handler(file_path.suffix)
        if not handler:
            logging.info(f"Unsupported file: {file_path}")
            return False
            
        return True
