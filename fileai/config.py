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

# Folder configuration - tuples of (folder_name, description)
FOLDERS = [
    ("medical", "Medical documents, prescriptions, treatment records"),
    (
        "financial",
        "Bank statements, invoices, payments, transfers, tax returns, tax-related documents, Purchase receipts and invoices",
    ),
    ("travel", "Travel itineraries, tickets, and reservations"),
    ("personal", "Personal documents and private files"),
    ("car", "Car related documents, tickets, fines, insurance"),
    ("home", "Mortgage, rent, utilities, and home insurance"),
    ("work", "Employment contracts, pay slips, work-related documents"),
    ("education", "School records, diplomas, certificates, transcripts, school forms"),
    ("government", "Government-issued documents, IDs, passports"),
    (
        "visa-immigration",
        "Any visa/immigration related document that doesn't fall under the government folder",
    ),
    ("legal", "Legal documents and contracts"),
    ("misc", "Miscellaneous uncategorized documents"),
]

PROMPT = """
Document Naming Assistant Task

Purpose: Analyze a document and create a standardized, descriptive filename that makes it easy to identify the content.

Input: 
- Original filename: {relative_file_path}. If the file name already contains useful information, you can use it in the new filename.
- Document content (may be OCRed text with potential errors)

Process:

    List these key elements (brief, no explanations):

    type: Document type. Some examples, invoice, bill, fine, ticket, leaflet, prescription, report, letter, email, contract, agreement, specification, manual, guide, form, certificate, statement, receipt, boarding pass, painting, photo, note, etc.
    date: Document date (could be year, year-month, or full date) Use YYYY-MM-DD format. Can be empty string. Sometimes this fill be the year / month the document refers to. For example a statement for 2024 February issued in March would have 2024 February. Tax documents covering year X should have year X.
    topic: The main subject or topic of the document. What is this document about? This will be part of the file name. Be specific and descriptive.
    owner: The main person or entity involved in the document. If it's a family member (one of the Herdağdelens or family) use their first name only.
    folder: The folder where the document should be stored. Choose from the folders defined below. If none of the folders are a good match return misc.
    keywords: list[str]: list of keywords that describe the document content. These can be extracted from the content or the document itself.
    
    use kebap-case in all your responses (lowercase with hyphens) and avoid using special characters or spaces. limit to ascii, digits and hypen.
    
    Files should be organized into the following categories based on content. You can return other keywords as well.

{folders_list}
"""

def generate_folders_list():
    """Generate formatted string of folders and their descriptions"""
    return "\n".join(
        f"    {folder}/\n    - {description}\n"
        for folder, description in FOLDERS
    )
