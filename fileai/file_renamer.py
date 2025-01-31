import logging
from pathlib import Path
import re

from fileai.config import PROMPT, generate_folders_list


class FileRenamer:
    def __init__(self, api):
        self.api = api
        self.filename_pattern = re.compile(
            r"<filename>\s*(.*?)\s*</filename>", re.DOTALL | re.MULTILINE
        )
        self.keyword_pattern = re.compile(
            r"<keywords>\s*(.*?)\s*</keywords>", re.DOTALL | re.MULTILINE
        )
        self.ensure_output_structure()


    def categorize_file(self, options):
        prompt = PROMPT.format(
            relative_file_path=options.get("relative_file_path", ""),
            folders_list=generate_folders_list()
        )
        response = self.api.process_content_with_llm(
            prompt=prompt,
            content=options.get("content", ""),
            asset=options.get("asset", []),
        )
        # type = response['doc_type']
        owner = response["doc_owner"]
        topic = response["doc_topic"]
        date = response["doc_date"]
        filename = '-'.join(filter(None, [topic, date, owner]))
        filename = self.asciify_and_lowercase(filename)
        filename = self.sanitize_filename(filename)
        folder = response["doc_folder"]
        if not filename:
            logging.info(
                f"Error. Cannot extract file name from LLM response: {response}"
            )
            raise Exception()
        
        
        return filename, folder

    def asciify_and_lowercase(self, text):
        text = text.lower()
        text = text.replace("ç", "c")
        text = text.replace("ı", "i")
        text = text.replace("ü", "u")
        text = text.replace("ğ", "g")
        text = text.replace("ş", "s")
        text = text.replace(" ", "-")
        return text

    def sanitize_filename(self, filename):
        """Keep only a-z, 0-9, and - in the filename."""
        return re.sub(r"[^a-z0-9-]", "", filename)

    def ensure_output_structure(self):
        """Create the standard directory structure in the output directory if it doesn't exist."""
        base_dir = Path("output")

        # Standard categories
        categories = [
            "medical",
            "financial",
            "travel",
            "personal",
            "technical",
            "legal",
            "receipts",
            "misc",
        ]

        # Create directories
        for category in categories:
            category_dir = base_dir / category
            category_dir.mkdir(parents=True, exist_ok=True)
