import logging
from pathlib import Path
from typing import Optional, Tuple

from fileai import document_handlers
from fileai.document_categorizer import DocumentCategorizer
from fileai.config import Asset
from fileai.directory_manager import DirectoryManager
from fileai.filesystem_manager import FileSystemManager

class DocumentProcessor:
    """Orchestrates the document processing workflow"""

    def __init__(self, input_dir: Path, output_dir: Path, api):
        self.input_dir = input_dir.resolve()
        self.output_dir = output_dir.resolve()
        self.dir_manager = DirectoryManager(output_dir)
        self.categorizer = DocumentCategorizer(api)
        self.fs_manager = FileSystemManager()
        
        # Initialize directory structure
        self.dir_manager.ensure_category_structure()

    def process_document(self, file_path: Path) -> Optional[Path]:
        """
        Process a single document through the complete workflow.
        Returns the new file path if successful, None otherwise.
        """
        if not self._validate_document(file_path):
            return None

        try:
            # Extract content and metadata
            content, asset = self._extract_content(file_path)
            if content is None and not asset:
                return None

            # Get relative path for logging, use str representation if relative_to fails
            try:
                relative_path = str(file_path.relative_to(self.input_dir))
            except ValueError:
                relative_path = str(file_path)

            # Prepare options for categorization
            options = {
                "content": content,
                "asset": asset,
                "relative_file_path": relative_path
            }

            # Categorize document and generate filename
            filename, category = self.categorizer.categorize_document(options)

            # Generate new file path
            category_path = self.dir_manager.get_category_path(category)
            new_base_path = category_path / f"{filename}{file_path.suffix}"

            # Handle potential duplicates
            if self.fs_manager.is_same_file(file_path, new_base_path):
                logging.info(f"Duplicate file found, removing: {relative_path}")
                self.fs_manager.remove_file(file_path)
                return None

            # Ensure unique filename if destination exists
            if new_base_path.exists():
                new_base_path = self.fs_manager.ensure_unique_path(new_base_path)

            # Move the file
            final_path = self.fs_manager.move_file(file_path, new_base_path)
            
            # Cleanup empty directories
            self.dir_manager.cleanup_empty_dirs(file_path.parent, self.input_dir)
            
            logging.info(f"Processed: {relative_path} -> {final_path.relative_to(self.output_dir)}")
            return final_path

        except Exception as e:
            logging.error(f"Error processing document {file_path}: {e}")
            return None

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

    def _extract_content(self, file_path: Path) -> Tuple[Optional[str], Optional[Asset]]:
        """Extract content and metadata from document."""
        handler = document_handlers.get_handler(file_path.suffix)
        if handler:
            content, asset = handler.process(file_path)
            if asset is None:
                asset = Asset(file_type=handler.file_type)
            return content, asset
        return None, None
