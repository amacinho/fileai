from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Optional

from fileai import document_handlers
from fileai.document_categorizer import DocumentCategorizer
from fileai.file_operator import FileOperator

@dataclass
class PipelineState:
    original_path: Optional[Path] = None
    temporary_path: Optional[Path] = None
    category: Optional[str] = None
    target_path: Optional[Path] = None
    filename: Optional[str] = None
    api_sucess: Optional[bool] = None

    def reset(self):
        self.original_path = None
        self.temporary_path = None
        self.category = None
        self.target_path = None
        self.filename = None
        self.api_sucess = False
        
class DocumentPipeline:
    """Pipeline for processing documents through the complete workflow."""
    def __init__(self, categorizer: DocumentCategorizer, file_operator: FileOperator):
        self.categorizer = categorizer
        self.file_operator = file_operator
    
    def process(self, file_path: Path) -> Path:
        """Process document through the complete pipeline."""
        self.state = PipelineState(original_path=file_path)
        try:
            # Extract and categorize content
            (self.extract_content()
             .categorize()
             .move_to_destination()
             )
            return self.state.target_path
        except Exception as e:
            logging.error(f"Failed to process file {file_path}: {e}")
            # Move failed file to unsupported
            return self.file_operator.move_to_unsupported(file_path)
        finally:
            self.state = None

    def extract_content(self) -> 'DocumentPipeline':
        """Extract content from the document using appropriate handler."""
        if not self.state:
            raise ValueError("Pipeline state not initialized")
        self._handler = document_handlers.get_handler(self.state.original_path.suffix)
        if self._handler:
            self.file_type = self._handler.file_type
            self.state.temporary_path = self._handler.process(self.state.original_path)
        else:
            raise ValueError(f"Unsupported file type: {self.state.original_path.suffix}")
        return self

    def categorize(self) -> 'DocumentPipeline':
        """Categorize document using the API."""
        if not self.state.temporary_path:
            raise ValueError("Cannot categorize document: temporary_path not set")
        
        filename, category = self.categorizer.categorize_document(
            path=self.state.temporary_path,
            original_path=self.state.original_path
        )
        if filename and category:
            self.state.filename = filename
            self.state.category = category
        return self

    def move_to_destination(self) -> 'DocumentPipeline':
        """Move document to its final destination."""
        if not self.state.category:
            raise ValueError("Cannot move document: category not set")
        if not self.state.filename:
            raise ValueError("Cannot move document: filename not set")
        
        category_path = self.file_operator.output_base_path / self.state.category
        category_path.mkdir(parents=True, exist_ok=True)
        new_path = category_path / f"{self.state.filename}{self.state.original_path.suffix}"
        
        # Check for hash-based duplicates
        existing_duplicate = self.file_operator.find_duplicate_by_hash(self.state.original_path)
        if existing_duplicate:
            # Create versioned filename starting with _v2
            base_name = f"{existing_duplicate.stem}_v2{existing_duplicate.suffix}"
            new_path = existing_duplicate.parent / base_name
            new_path = self.file_operator.ensure_unique_path(new_path)
            logging.info(f"Duplicate file found by hash, creating versioned copy: {new_path}")
        else:
            # Ensure unique filename
            if new_path.exists():
                new_path = self.file_operator.ensure_unique_path(new_path)

        # Copy file to destination
        try:
            self.state.target_path = self.file_operator.copy_file(self.state.original_path, new_path)
            # Update hash dictionary with the new file
            self.file_operator._update_hash_dict(self.state.target_path)
        except OSError as e:
            logging.error(f"Failed to copy file: {e}")
            self.state.target_path = None
            return self

        # Remove original file only after successful copy
        if self.file_operator.remove_input_files:
            try:
                self.file_operator.remove_file(self.state.original_path)
            except OSError as e:
                logging.error(f"File copied, but failed to remove input file: {e}")
                self.state.target_path = None
                return self
