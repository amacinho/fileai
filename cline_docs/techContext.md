# Technical Context

## Technologies Used

1. **Core Technologies**
   - Python 3.x
   - Watchdog for file system monitoring
   - PyPDF2 for PDF processing
   - PIL/Pillow for image processing

2. **API Integration**
   - Gemini API
   - Rate limiting implementation
   - Structured response handling

3. **File Handling**
   - Support for multiple file types:
     - Images: JPG, PNG, GIF, BMP, TIFF, WEBP, HEIC
     - Documents: DOC, DOCX
     - Spreadsheets: XLS, XLSX
     - PDFs
     - Text files: TXT, CSV, MD, HTML, XML, JSON, YAML, RTF

4. **Configuration**
   - Environment variables
   - JSON config file
   - Cross-platform config directory handling

## Development Setup

1. **Dependencies**
   - Managed via requirements.txt
   - Core dependencies:
     - watchdog
     - PyPDF2
     - Pillow
     - python-dotenv

2. **Logging**
   - Comprehensive logging system
   - Configurable log level
   - Detailed error tracking

3. **Testing**
   - Unit tests for core functionality
   - Integration tests for API interactions
   - End-to-end tests for complete workflows
   - Test fixtures for various scenarios

## Technical Constraints

1. **Rate Limiting**
   - 14 API calls per minute
   - Automatic wait calculation
   - Queue-based implementation

2. **File Size**
   - Image resizing to 1024x1024
   - PDF processing limited to first 2 pages

3. **Security**
   - Input/output path validation
   - Safe file operations
   - Proper resource cleanup
