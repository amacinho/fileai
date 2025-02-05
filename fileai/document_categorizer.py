import logging
import re
from pathlib import Path
from typing import Tuple

from fileai.config import PROMPT, generate_folders_list

class DocumentCategorizer:
    """Handles document categorization and naming using AI"""

    def __init__(self, api):
        self.api = api

    def categorize_document(self, path: Path) -> Tuple[str, str]:
        """
        Categorize a document using AI and generate appropriate name.
        Returns: (filename, category)
        """
        prompt = PROMPT.format(
            relative_file_path=path,
            folders_list=generate_folders_list()
        )
        
        response = self.api.get_response(
            prompt=prompt,
            path=path
        )

        owner = response["doc_owner"]
        topic = response["doc_topic"]
        date = response["doc_date"]
        
        filename = self._generate_filename(topic, date, owner)
        category = response["doc_folder"]

        if not filename:
            logging.error(f"Error: Cannot extract filename from LLM response: {response}")
            raise ValueError("Invalid filename generated")

        return filename, category

    def _generate_filename(self, topic: str, date: str, owner: str) -> str:
        """Generate a standardized filename from components."""
        filename = '-'.join(filter(None, [topic, date, owner]))
        filename = self._asciify_and_lowercase(filename)
        return self._sanitize_filename(filename)

    def _asciify_and_lowercase(self, text: str) -> str:
        """Convert text to ASCII lowercase with specific character replacements."""
        text = text.lower()
        replacements = {
            'ç': 'c', 'ı': 'i', 'ü': 'u', 'ğ': 'g', 'ş': 's',
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        text = re.sub(r'\s+', '-', text)
        return text

    def _sanitize_filename(self, filename: str) -> str:
        """Keep only a-z, 0-9, and - in the filename."""
        return re.sub(r"[^a-z0-9-]", "", filename)
