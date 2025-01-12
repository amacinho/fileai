import hashlib
import logging
import os
from pathlib import Path
import shutil

from fileai.api import GeminiAPI
from fileai.config import Asset
from fileai.config import (SUPPORTED_DOC_EXTENSIONS, SUPPORTED_EXTENSIONS, SUPPORTED_IMAGE_EXTENSIONS, SUPPORTED_TEXT_EXTENSIONS)
from fileai.file_renamer import FileRenamer

class FileOrganizer:
    def __init__(self, input_dir_path: Path, output_dir_path: Path, api: GeminiAPI):
        self.input_dir_path = input_dir_path.resolve()
        self.output_dir_path = output_dir_path.resolve()
        self.api = api
        self.file_renamer = FileRenamer(self.api)

    def _move_file(self, current_file_name: Path, new_file_name: Path) -> Path:
        """Move the file to the new destination with the new name."""
        target_folder = new_file_name.parent
        target_folder.mkdir(parents=True, exist_ok=True)
        shutil.move(current_file_name, new_file_name)
        return new_file_name

    def _remove_file(self, file_path: Path):
        """Remove the file."""
        os.remove(file_path)

    def is_processable_file(self, file_path: Path) -> bool:
        """Check if a file is processable based on its extension."""
        return file_path.suffix.lower() in SUPPORTED_EXTENSIONS

    def is_image(self, file_path: Path) -> bool:
        """Check if a file is an image based on its extension."""
        return file_path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS

    def is_text(self, file_path: Path) -> bool:
        """Check if a file is a text file based on its extension."""
        return file_path.suffix.lower() in SUPPORTED_TEXT_EXTENSIONS

    def is_pdf(self, file_path: Path) -> bool:
        """Check if a file is a PDF based on its extension."""
        return file_path.suffix.lower() == ".pdf"

    def is_doc(self, file_path: Path) -> bool:
        """Check if a file is a doc based on its extension."""
        return file_path.suffix.lower() in SUPPORTED_DOC_EXTENSIONS

    def read_document_content(self, file_path):
        """
        Placeholder method for processing document type (.doc) files.
        """
        raise NotImplementedError(
            f"Document processing is not supported yet for {file_path}"
        )

    def save_file(self, current_file_name: Path, new_file_name: Path) -> Path:
        """Move the file to the new destination with the new name."""
        return self._move_file(current_file_name=current_file_name, new_file_name=new_file_name)

    def read_text_content(self, file_path: Path) -> str:
        """Read the content of a text file."""
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return file.read()
        except Exception as e:
            logging.error(f"Failed to read file content {file_path}: {e}")
            return ""

    def compute_hash(self, file_path: Path) -> str:
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

    def _extract_content(self, file_path: Path) -> tuple[str, Asset]:
        """
        Extract content and media from a file.
        Returns a tuple of (text_content, media_list) where media_list contains Asset objects.
        """
        content = ""
        asset = None

        mime_type = None
        if self.is_image(file_path):
            mime_type = f"image/{file_path.suffix.lower()[1:]}"
        elif self.is_pdf(file_path):
            mime_type = "application/pdf"
        elif self.is_doc(file_path):
            mime_type = "application/octet-stream"

        if mime_type and not self.is_doc(file_path):
            asset = Asset(str(file_path), mime_type)
        elif self.is_text(file_path):
            content = self.read_text_content(file_path)
        elif self.is_doc(file_path):
            content = self.read_document_content(file_path)

        return content, asset

    def _preprocess_file(self, file_path: Path) -> dict:
        """Preprocesses a file, extracting content and preparing options."""
        if file_path.name == ".DS_Store":
            return None

        try:
            resolved_file_path = file_path.resolve()
            logging.debug(f"Resolved file path: {resolved_file_path}")
            logging.debug(f"Input directory path: {self.input_dir_path}")
            
            try:
                relative_file_path = resolved_file_path.relative_to(self.input_dir_path)
            except ValueError:
                # If the file is not in the input directory, try using the original path
                relative_file_path = file_path
                logging.debug(f"Using original path as relative path: {relative_file_path}")
            
            if not self.is_processable_file(file_path):
                logging.info(f"Unsupported file: {relative_file_path}")
                return None

            content, asset = self._extract_content(file_path)
            if content is None and not asset:
                logging.error(f"Failed to extract content or asset from {file_path}")
                return None

            options = {
                "asset": asset,
                "content": content,
                "relative_file_path": str(relative_file_path),
            }
            return options
        except Exception as e:
            logging.error(f"Error preprocessing file {file_path}: {e}")
            return None

    def _generate_new_file_path(self, current_file_path: Path, options: dict) -> Path:
        """Generates the new file path, handling versioning if necessary."""
        new_name, new_folder = self.file_renamer.categorize_file(options)
        if not new_name:
            logging.error(
                f"Failed to extract filename from LLM response for {current_file_path}"
            )
            return None

        i = None
        while True:
            version = f"_{i}" if i is not None else ""
            new_file_path = (
                self.output_dir_path
                / new_folder
                / f"{new_name}{version}{current_file_path.suffix}"
            )
            if not new_file_path.exists():
                return new_file_path
            else:
                existing_file_hash = self.compute_hash(new_file_path)
                current_file_hash = self.compute_hash(current_file_path)
                if existing_file_hash == current_file_hash:
                    try:
                        relative_path = current_file_path.relative_to(self.input_dir_path)
                    except ValueError:
                        relative_path = current_file_path
                    logging.info(f"A file with the same name and hash already exists, skipped: {relative_path}")
                    self._remove_file(current_file_path)
                    return None
                else:
                    try:
                        relative_path = current_file_path.relative_to(self.input_dir_path)
                    except ValueError:
                        relative_path = current_file_path
                    logging.warning(
                        f"A file with the same name but different content already exists: {relative_path}. Will try to save with a version number."
                    )
                    i = 1 if i is None else i + 1
                    continue

    def _save_or_skip_file(self, current_file_path: Path, new_file_path: Path) -> None:
        """Saves the file or skips if a file with the same name and hash exists."""
        if not new_file_path:
            return
        try:
            self.save_file(
                current_file_name=current_file_path,
                new_file_name=new_file_path,
            )
            try:
                relative_current_file_path = current_file_path.relative_to(self.input_dir_path)
            except ValueError:
                relative_current_file_path = current_file_path
                
            try:
                relative_new_file_path = new_file_path.relative_to(self.output_dir_path)
            except ValueError:
                relative_new_file_path = new_file_path
            logging.info(f"Renamed: {relative_current_file_path} to {relative_new_file_path}")
        except FileExistsError:
            try:
                relative_path = current_file_path.relative_to(self.input_dir_path)
            except ValueError:
                relative_path = current_file_path
            logging.warning(
                f"Not overwriting existing file with the same name: {relative_path}"
            )

    def organize_file(self, current_file_path: Path) -> None:
        """Organize a single file by categorizing and moving it to the appropriate location."""
        options = self._preprocess_file(current_file_path)
        if not options:
            return

        new_file_path  = self._generate_new_file_path(current_file_path, options)
        self._save_or_skip_file(current_file_path, new_file_path)
        
        # Check if parent directory is empty and delete it if it's not the watch directory
        parent_dir = current_file_path.parent
        while parent_dir != self.input_dir_path and self._is_empty_dir(parent_dir):
            try:
                os.rmdir(parent_dir)
                logging.info(f"Deleted empty directory: {parent_dir.relative_to(self.input_dir_path)}")
                # Move up to check if parent is also empty
                parent_dir = parent_dir.parent
            except OSError:
                break  # Stop if we can't remove the directory

    def _is_empty_dir(self, dir_path: Path) -> bool:
        """Check if a directory is empty."""
        if not dir_path.is_dir():
            return False
        try:
            return not any(os.scandir(dir_path))
        except Exception:
            return False

    def organize_directory(self) -> None:
        """Organize all files in the input directory, processing deeper files first."""
        try:
            # Get all files and sort by directory depth
            files = list(self.input_dir_path.rglob("*"))
            files.sort(key=lambda p: len(p.parents), reverse=True)
            for file_path in files:
                try:
                    # Skip directories and files in output folder
                    if file_path.is_dir() or file_path.is_relative_to(
                        self.output_dir_path
                    ):
                        continue

                    self.organize_file(file_path)

                except NotImplementedError:
                    logging.info(
                        f"Processing not implemented for types of {file_path.name}"
                    )
                except Exception as e:
                    try:
                        relative_path = file_path.relative_to(self.input_dir_path)
                    except ValueError:
                        relative_path = file_path
                    logging.error(
                        f"Error processing file {relative_path}: {e}"
                    )

        except Exception as err:
            raise err
