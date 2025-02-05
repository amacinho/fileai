import hashlib
import logging
import os
import shutil
from pathlib import Path
from typing import Dict, Optional

from fileai.directory_manager import DirectoryManager

class FileOperator:
    """Handles file system operations"""
    def __init__(self, input_base_path: Path, output_base_path: Path, remove_input_files=True):
        self.output_base_path = output_base_path
        self.input_base_path = input_base_path
        self.remove_input_files = remove_input_files
        self.unsupported_path = output_base_path / "unsupported"
        self.unsupported_path.mkdir(parents=True, exist_ok=True)
        self.directory_manager = DirectoryManager(self.input_base_path)

    def _cleanup_after_operation(self, file_path: Path) -> None:
        """Clean up empty directories after file operations."""
        if file_path.is_relative_to(self.input_base_path):
            self.directory_manager.cleanup_empty_dirs(
                start_path=file_path.parent,
                stop_path=self.input_base_path
            )

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
        self._cleanup_after_operation(source)
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
        self._cleanup_after_operation(source)
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
            self._cleanup_after_operation(file_path)
        except Exception as e:
            logging.error(f"Error removing file {file_path}: {e}")

    def compute_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of a file."""
        hasher = hashlib.sha256()
        try:
            with open(file_path, "rb") as file:
                while True:
                    chunk = file.read(4096)
                    if not chunk:
                        break
                    hasher.update(chunk)
            return hasher.hexdigest()
        except OSError:
            return None
        except Exception as e:
            logging.error(f"Error computing hash for file {file_path}: {e}")
            raise
        
    def is_same_file(self, file1: Path, file2: Path) -> bool:
        """Check if two files are identical based on their size and hash."""
        if not file1.exists() or not file2.exists():
            return False
        
        # First check if file sizes are the same
        if file1.stat().st_size != file2.stat().st_size:
            return False
            
        # Then compare hashes
        hash1 = self.compute_hash(file_path=file1)
        hash2 = self.compute_hash(file_path=file2)
        return hash1 is not None and hash2 is not None and hash1 == hash2

    def read_text_content(self, file_path: Path) -> Optional[str]:
        """Read the content of a text file."""
        with open(file_path, "r", encoding="utf-8") as file:
           return file.read()
        
    def move_to_unsupported(self, file_path: Path) -> Path:
        """Move a failed/unsupported file to the unsupported directory."""
        # First check if we already have an identical file in unsupported
        duplicate = self.find_duplicate_by_hash(file_path)
        if duplicate and duplicate.is_relative_to(self.unsupported_path):
            # If duplicate exists in unsupported, remove the new file
            self.remove_file(file_path)
            return duplicate
            
        # No duplicate found, move the file with versioned name if needed
        unsupported_path = self.unsupported_path / file_path.name
        unsupported_path = self.ensure_unique_path(unsupported_path)
        result = self.move_file(file_path, unsupported_path)
        self._cleanup_after_operation(file_path)
        return result

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

    def scan_output_directory(self) -> None:
        """Scan output directory and build hash dictionary."""
        self.file_hash_dict = {}
        self.file_size_dict = {}  # Store file sizes for quick lookup
        
        for file_path in self.output_base_path.rglob('*'):
            if file_path.is_file():
                try:
                    file_size = file_path.stat().st_size
                    file_hash = self.compute_hash(file_path)
                    
                    if file_hash:
                        # Store file in hash dictionary
                        if file_hash not in self.file_hash_dict:
                            self.file_hash_dict[file_hash] = []
                        self.file_hash_dict[file_hash].append(file_path)
                        # Sort paths alphabetically
                        self.file_hash_dict[file_hash].sort()
                        
                        # Store file size
                        self.file_size_dict[str(file_path)] = file_size
                except (FileNotFoundError, PermissionError) as e:
                    logging.error(f"Error accessing file {file_path}: {e}")

    def find_duplicate_by_hash(self, file_path: Path) -> Optional[Path]:
        """Check if file has duplicate in output directory by size and hash."""
        if not hasattr(self, 'file_hash_dict'):
            self.scan_output_directory()
        
        # Get file size
        try:
            file_size = file_path.stat().st_size
        except (FileNotFoundError, PermissionError):
            return None
            
        # Compute hash only if file exists
        file_hash = self.compute_hash(file_path)
        if not file_hash:
            return None
            
        # Check if hash exists in dictionary
        if file_hash in self.file_hash_dict:
            # Verify the first file with matching hash also has matching size
            first_match = self.file_hash_dict[file_hash][0]
            try:
                if first_match.stat().st_size == file_size:
                    return first_match
            except (FileNotFoundError, PermissionError):
                # If we can't access the file, skip it
                pass
                
        return None

    def get_duplicate_stats(self) -> Dict[str, int]:
        """Get statistics about duplicate files."""
        if not hasattr(self, 'file_hash_dict'):
            self.scan_output_directory()
            
        stats = {
            'total_files': 0,
            'unique_files': 0,
            'duplicate_files': 0,
            'duplicate_groups': 0
        }
        
        for file_hash, paths in self.file_hash_dict.items():
            stats['total_files'] += len(paths)
            if len(paths) > 1:
                stats['duplicate_files'] += len(paths) - 1
                stats['duplicate_groups'] += 1
            else:
                stats['unique_files'] += 1
                
        return stats

    def _update_hash_dict(self, file_path: Path) -> None:
        """Update hash dictionary with new file."""
        if not hasattr(self, 'file_hash_dict') or not hasattr(self, 'file_size_dict'):
            self.scan_output_directory()
            
        try:
            # Get file size
            file_size = file_path.stat().st_size
            # Compute hash
            file_hash = self.compute_hash(file_path)
            
            if file_hash:
                # Update hash dictionary
                if file_hash not in self.file_hash_dict:
                    self.file_hash_dict[file_hash] = []
                self.file_hash_dict[file_hash].append(file_path)
                # Keep paths sorted
                self.file_hash_dict[file_hash].sort()
                
                # Update size dictionary
                self.file_size_dict[str(file_path)] = file_size
        except (FileNotFoundError, PermissionError) as e:
            logging.error(f"Error updating hash dictionary for {file_path}: {e}")
