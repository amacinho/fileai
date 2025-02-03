# FileAI

A Python package for organizing and renaming files using AI.

## Quick Start

```bash
git clone https://github.com/amacinho/fileai.git
cd fileai
pip install .
mkdir -p ~/tmp/documents/categorized
fileai --api-key <ADD YOUR GEMINI API KEY> --monitor ~/tmp/documents ~/tmp/documents/categorized gemini --model gemini-1.5-flash
# fileai will start monitoring ~/tmp/documents for new files and categorize them under ~/tmp/documents/categorized.
```

## Configuration

FileAI requires a Gemini API key to function. You can provide your API key in one of three ways:

1. **Environment Variable**
   ```bash
   export GEMINI_API_KEY=your-api-key
   ```

2. **Configuration File**
   Create a JSON configuration file at `~/.fileai/config.json` (Linux/Mac) or `%APPDATA%\fileai\config.json` (Windows):
   ```json
   {
     "api_key": "your-api-key",
     "model": "model-name" # defaults to gemini-2.0-flash-exp
   }
   ```

3. **Direct Initialization**
   ```python
   from fileai.api import GeminiAPI
   
   api = GeminiAPI(api_key="your-api-key")
   ```

The API key precedence is:
1. Direct initialization
2. Configuration file
3. Environment variable

## Usage

### Command Line Interface

```bash
# Basic usage
fileai input_directory output_directory gemini

# With API key provided via command line
fileai input_directory output_directory gemini --api-key your-api-key

# With custom model
fileai input_directory output_directory gemini --model gemini-pro-vision

# Customize polling interval for file watching
fileai input_directory output_directory gemini --poll-interval 30
```

### Python API

```python
from fileai import FileOrganizer
from fileai.api import GeminiAPI

# Initialize the API client (will use config file or environment variables if not provided)
api = GeminiAPI(api_key="your-api-key")  # api_key is optional if configured elsewhere

# Initialize the organizer
organizer = FileOrganizer(input_path="input_dir", output_path="output_dir", api=api)

# Process a single file
organizer.process_file("path/to/your/file.pdf")

# Process a directory
organizer.process_directory("path/to/your/directory")
```

## Features

- Automatically analyzes documents using AI
- Organizes files into appropriate categories
- Generates descriptive filenames based on content
- Supports various file types:
  - PDF documents
  - Images (jpg, png, etc.)
  - Text files
  - Office documents (docx, xlsx, etc.)
