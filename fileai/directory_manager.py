import logging
from pathlib import Path
from typing import Optional

from fileai.config import FOLDERS

class DirectoryManager:
    """Manages directory structure and operations"""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir.resolve()

    def ensure_category_structure(self) -> None:
        """Create the standard directory structure if it doesn't exist."""
        for folder_name, _ in FOLDERS:
            category_dir = self.base_dir / folder_name
            category_dir.mkdir(parents=True, exist_ok=True)

    def get_category_path(self, category: str) -> Path:
        """Get path for a specific category."""
        valid_categories = {folder_name for folder_name, _ in FOLDERS}
        if category not in valid_categories:
            logging.warning(f"Unknown category: {category}, using 'misc'")
            category = "misc"
        return self.base_dir / category

    def cleanup_empty_dirs(self, start_path: Path, stop_path: Path) -> None:
        """Remove empty directories recursively up to stop_path."""
        if not start_path.is_dir():
            return

        current_path = start_path
        while current_path != stop_path and self._is_empty_dir(current_path):
            try:
                current_path.rmdir()
                logging.info(f"Deleted empty directory: {current_path.relative_to(stop_path)}")
                current_path = current_path.parent
            except OSError:
                break

    def _is_empty_dir(self, dir_path: Path) -> bool:
        """Check if a directory is empty, ignoring @eaDir folders.
        A directory containing only @eaDir is considered empty."""
        if not dir_path.is_dir():
            return False
        try:
            return not any(
                item for item in dir_path.iterdir()
                if not (item.is_dir() and item.name == "@eaDir")
            )
        except Exception:
            return False

    def get_relative_path(self, path: Path) -> Optional[Path]:
        """Get path relative to base directory."""
        try:
            return path.relative_to(self.base_dir)
        except ValueError:
            return None
