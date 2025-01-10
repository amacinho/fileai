import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}

if log_level not in VALID_LOG_LEVELS:
    print(f"Invalid LOG_LEVEL: {log_level}. Defaulting to INFO")
    log_level = "ERROR"

logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Configuration handling
def get_config_dir():
    """Get the configuration directory for fileai."""
    if os.name == 'nt':  # Windows
        config_dir = Path(os.environ.get('APPDATA', '~')) / 'fileai'
    else:  # Unix-like
        config_dir = Path('~/.config/fileai').expanduser()
    return config_dir

def get_config_file():
    """Get the configuration file path."""
    return get_config_dir() / 'config.json'

def load_config():
    """Load configuration from various sources."""
    config = {}
    
    # Try loading from config file
    config_file = get_config_file()
    if config_file.exists():
        try:
            with open(config_file) as f:
                config = json.load(f)
        except Exception as e:
            logging.warning(f"Error loading config file: {e}")
    
    # Environment variables take precedence
    if os.getenv("GEMINI_API_KEY"):
        config["api_key"] = os.getenv("GEMINI_API_KEY")
    if os.getenv("GEMINI_MODEL"):
        config["model"] = os.getenv("GEMINI_MODEL")
    
    return config

def save_config(config):
    """Save configuration to file."""
    config_dir = get_config_dir()
    config_file = get_config_file()
    
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        logging.error(f"Error saving config file: {e}")
        raise

# Define constants
SUPPORTED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".tiff",
    ".tif",
    ".webp",
    ".heic",
}
SUPPORTED_TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".csv",
    ".json",
    ".xml",
    ".html",
    ".log",
    ".yaml",
    ".yml",
}
SUPPORTED_DOC_EXTENSIONS = {".docx", ".doc", ".xls", ".xlsx", ".ppt", ".pptx"}
SUPPORTED_EXTENSIONS = (
    {".pdf"}
    | SUPPORTED_IMAGE_EXTENSIONS
    | SUPPORTED_TEXT_EXTENSIONS
    | SUPPORTED_DOC_EXTENSIONS
)

class Asset:
    """Image/Doc or PDF asset to be processed."""

    def __init__(self, path: str, mime_type: str):
        self.path = path
        self.mime_type = mime_type
        self.type = self._determine_type()

    def _determine_type(self):
        extension = os.path.splitext(self.path)[1].lower()
        if extension in SUPPORTED_IMAGE_EXTENSIONS:
            return "image"
        elif extension == ".pdf":
            return "pdf"
        elif extension in SUPPORTED_TEXT_EXTENSIONS:
            return "text"
        elif extension in SUPPORTED_DOC_EXTENSIONS:
            return "doc"
        return None

PROMPT = """
Document Naming Assistant Task

Purpose: Analyze a document and create a standardized, descriptive filename that makes it easy to identify the content.

Input: 
- Original filename: {relative_file_path}. If the file name already contains useful information, you can use it in the new filename.
- Document content (may be OCRed text with potential errors)

Process:

    List these key elements (brief, no explanations):

    type: Document type. Some examples, invoice, bill, fine, ticket, leaflet, prescription, report, letter, email, contract, agreement, specification, manual, guide, form, certificate, statement, receipt, boarding pass, painting, photo, note, etc.
    date: Document date (could be year, year-month, or full date) Use YYYY-MM-DD format. Can be empty string.
    topic: The main subject or topic of the document. What is this document about? This will be part of the file name. Be specific and descriptive.
    owner: The main person or entity involved in the document. If it's a family member (one of the Herdağdelens or family) use their first name only.
    folder: The folder where the document should be stored. Choose from the folders defined below. If none of the folders are a good match return misc.
    keywords: list[str]: list of keywords that describe the document content. These can be extracted from the content or the document itself.
    
    use kebap-case in all your responses (lowercase with hyphens) and avoid using special characters or spaces. limit to ascii, digits and hypen.
    
    Files should be organized into the following categories based on content. Use the keywords gıven below as suggestions. You can return other keywords as well.

    medical/
    - Medical documents, prescriptions, treatment records
    - Keywords: prescription, hospital, medical, augmentin, treatment, doctor, health

    financial/
    - Bank statements, invoices, payments, transfers
    - Keywords: bank, statement, invoice, fattura, payment, bonifico, transfer

    travel/
    - Boarding passes, flight documents
    - Keywords: boarding, flight, airlines, travel

    personal/
    - Letters, family documents, certificates
    - Keywords: letter, family, certificate, residence

    home/
    - Mortgage, rent, etc.
    - Keywords: mortgage, rent, lease, utilities, electricity, gas, water, internet, phone, mobile, gas, electricity, water, internet, phone, mobile

    car/
    - Car related documents, tickets, fines, insurance
    - Keywords: ticket, multa, fine, traffic, car, insurance

    technical/
    - Hardware specifications, setup instructions
    - Keywords: hardware, router, computer, specification, setup

    legal/
    - Contracts, agreements, registrations
    - Keywords: contract, agreement, registration

    receipts/
    - Receipts and transaction records
    - Keywords: receipt, estratto

    misc/
    - Uncategorized documents
    - Default category when no other category matches
"""
