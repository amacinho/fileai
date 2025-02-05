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

    def reset(self):
        self.original_path = None
        self.temporary_path = None
        self.category = None
        self.target_path = None
        self.filename = None
        
class DocumentPipeline:
    """Pipeline for processing documents through the complete workflow."""
    def __init__(self, categorizer: DocumentCategorizer, file_operator: FileOperator):
        self.categorizer = categorizer
        self.file_operator = file_operator
    
    def process(self, file_path: Path) -> Path:
        """Process document through the complete pipeline."""
        try:
            self.state = PipelineState(original_path=file_path)
            (self.extract_content()
             .categorize()
             .move_to_destination())
            target_path = self.state.target_path
            return target_path
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
        
        filename, category = self.categorizer.categorize_document(self.state.temporary_path)
        if filename and category:
            self.state.filename = filename
            self.state.category = category
        return self

    def move_to_destination(self) -> 'DocumentPipeline':
        """Move document to its final destination."""
        if not self.state.category:
            raise ValueError("Cannot move document: category not set")
        # Ensure category is a valid folder name
        try:        
            category_path = self.file_operator.output_base_path / self.state.category
            category_path.mkdir(parents=True, exist_ok=True)
            new_path = (
                category_path / f"{self.state.filename}{self.state.original_path.suffix}"
            )
        except Exception as e:
            logging.error(f"Failed to create new path: {e}")
            raise e
        
        # Handle duplicates
        if self.file_operator.is_same_file(self.state.original_path, new_path):
            if (self.file_operator.remove_input_files):
                logging.info(f"Duplicate file found, removing: {self.state.original_path}")
                self.file_operator.remove_file(self.state.original_path)
            else:
                logging.info(f"Duplicate file found, skipping: {self.state.original_path}")
            self.state.target_path = None
            return self

        # Ensure unique filename
        if new_path.exists():
            new_path = self.file_operator.ensure_unique_path(new_path)

        # Move or copy file
        if self.file_operator.remove_input_files:
            self.state.target_path = self.file_operator.move_file(self.state.original_path, new_path)
        else:
            self.state.target_path = self.file_operator.copy_file(self.state.original_path, new_path)
        return self

    
