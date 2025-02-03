import hashlib
import logging
import os
import shutil
from pathlib import Path
from typing import Optional

class FileSystemManager:
    """Handles file system operations"""

    @staticmethod
    def move_file(source: Path, destination: Path) -> Path:
        """
        Move a file to a new location, creating directories as needed.
        Returns the new file path.
        """
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(source, destination)
        return destination

    @staticmethod
    def remove_file(file_path: Path) -> None:
        """Safely remove a file."""
        try:
            os.remove(file_path)
        except Exception as e:
            logging.error(f"Error removing file {file_path}: {e}")

    @staticmethod
    def compute_hash(file_path: Path) -> Optional[str]:
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
        except Exception as e:
            logging.error(f"Failed to compute hash for {file_path}: {e}")
            return None

    @staticmethod
    def is_same_file(file1: Path, file2: Path) -> bool:
        """Check if two files are identical based on their hash."""
        if not file1.exists() or not file2.exists():
            return False
        hash1 = FileSystemManager.compute_hash(file1)
        hash2 = FileSystemManager.compute_hash(file2)
        return hash1 is not None and hash2 is not None and hash1 == hash2

    @staticmethod
    def read_text_content(file_path: Path) -> Optional[str]:
        """Read the content of a text file."""
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return file.read()
        except Exception as e:
            logging.error(f"Failed to read file content {file_path}: {e}")
            return None

    @staticmethod
    def ensure_unique_path(base_path: Path) -> Path:
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
