import hashlib
import logging
import os
import shutil
from pathlib import Path
from typing import Optional

class FileOperator:
    """Handles file system operations"""
    def __init__(self, input_base_path: Path, output_base_path: Path, remove_input_files=True):
        self.output_base_path = output_base_path
        self.input_base_path = input_base_path
        self.remove_input_files = remove_input_files

    def move_file(self, source: Path, destination: Path) -> Path:
        """
        Move a file to a new location, creating directories as needed.
        Returns the new file path.
        """
        # Ensure source and destination are under the base paths
        if not self.remove_input_files:
            raise ValueError(
                f"Cannot move file {source} because remove_input_files is set to False"
            )
        if not source.is_relative_to(self.input_base_path):
            raise ValueError(f"Source file {source} is not under the input base path {self.input_base_path}")
        if not destination.is_relative_to(self.output_base_path):
            raise ValueError(f"Destination file {destination} is not under the output base path {self.output_base_path}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(source, destination)
        return destination
    
    def copy_file(self, source: Path, destination: Path) -> Path:
        """
        Move a file to a new location, creating directories as needed.
        Returns the new file path.
        """
        # Ensure source and destination are under the base paths
        if not source.is_relative_to(self.input_base_path):
            raise ValueError(
                f"Source file {source} is not under the input base path {self.input_base_path}"
            )
        if not destination.is_relative_to(self.output_base_path):
            raise ValueError(
                f"Destination file {destination} is not under the output base path {self.output_base_path}"
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return destination

    def remove_file(self, file_path: Path) -> None:
        """Safely remove a file."""
        # Ensure the file is under the input base path and move_files is set to True
        if not self.remove_input_files:
            raise ValueError(
                f"Cannot remove file {file_path} because remove_input_files is set to False"
            )
        if not file_path.is_relative_to(self.input_base_path):
            raise ValueError(f"Cannot remove file {file_path} because it is not under the input base path {self.input_base_path}")

        try:
            os.remove(file_path)
        except Exception as e:
            logging.error(f"Error removing file {file_path}: {e}")

    def compute_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of a file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as file:
            while True:
                chunk = file.read(4096)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()
        
    def is_same_file(self, file1: Path, file2: Path) -> bool:
        """Check if two files are identical based on their hash."""
        if not file1.exists() or not file2.exists():
            return False
        hash1 = FileOperator.compute_hash(file1)
        hash2 = FileOperator.compute_hash(file2)
        return hash1 is not None and hash2 is not None and hash1 == hash2

    def read_text_content(self, file_path: Path) -> Optional[str]:
        """Read the content of a text file."""
        with open(file_path, "r", encoding="utf-8") as file:
           return file.read()
        
    def ensure_unique_path(self, base_path: Path) -> Path:
        """
        Ensure a unique path by appending a version number if needed.
        Returns the unique path.
        """
        if not base_path.exists():
            return base_path

        directory = base_path.parent
        stem = base_path.stem
        suffix = base_path.suffix
        counter = 1

        while True:
            new_path = directory / f"{stem}_{counter}{suffix}"
            if not new_path.exists():
                return new_path
            counter += 1
