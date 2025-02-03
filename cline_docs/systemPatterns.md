# System Patterns

## Architecture Overview

### Core Components
1. **Document Processor**
   - Central orchestrator
   - Manages file processing workflow
   - Coordinates between components
   - Handles file type validation

2. **Document Handlers**
   - Factory pattern for file type handling
   - Base handler with simplified interface
   - Specialized handlers per file type
   - Focus on content extraction

3. **Directory Manager**
   - Manages folder structure
   - Handles directory operations
   - Ensures category directories exist
   - Cleans up empty directories

4. **Document Categorizer**
   - AI-based document classification
   - Uses LLM for content analysis
   - Generates standardized filenames
   - Determines appropriate categories

5. **File System Manager**
   - Low-level file operations
   - File movement and renaming
   - Error handling and recovery
   - Path management

6. **File System Watcher**
   - Monitors directories for changes
   - Triggers processing on new files
   - Handles file system events
   - Rate limiting for bulk operations

## Design Patterns

1. **Factory Pattern**
   - Used in document handlers
   - Dynamic handler selection based on file type
   - Extensible for new file types
   - Centralized handler registration

2. **Strategy Pattern**
   - Different strategies for different file types
   - Consistent interface across handlers
   - Pluggable processing algorithms

3. **Observer Pattern**
   - File system watching
   - Event-driven processing
   - Asynchronous operations

4. **Singleton Pattern**
   - Configuration management
   - Logging system
   - Rate limiter

## Technical Decisions

1. **File Type Support**
   - PDF: Using pdfplumber for text extraction
   - Images: PIL/Pillow for basic processing
   - Office Documents:
     * Word: python-docx for content extraction
     * Excel: pandas with openpyxl engine for spreadsheet handling
     * PowerPoint: Basic file type identification
   - Text: Built-in file operations
   - Focus on content over metadata

2. **Testing Strategy**
   - Pytest for test framework
   - Temporary directories for file operations
   - Mock objects for external services
   - Fixtures for test data
   - Simplified test assertions

3. **Error Handling**
   - Graceful degradation
   - Focused error logging
   - Basic error recovery
   - Clear error messages

4. **Configuration**
   - Environment variables for secrets
   - JSON config files for settings
   - Runtime configuration options
   - Default fallbacks

5. **Performance Considerations**
   - Rate limiting for API calls
   - Efficient file operations
   - Minimal processing overhead
   - Streamlined data structures

## Code Organization

```
fileai/
├── api.py              # API endpoints
├── config.py           # Configuration handling
├── content_adapter.py  # Content processing and adaptation
├── directory_manager.py # Directory operations
├── document_categorizer.py # AI-based document classification
├── document_handlers.py # Primary file type handlers
├── document_processor.py # Main orchestration
├── file_organizer.py   # Additional file organization logic
├── filesystem_manager.py # File operations
├── main.py             # Entry point
├── pdf_transformer.py  # PDF-specific transformations
├── rate_limiter.py     # API rate limiting
└── watcher.py          # File system monitoring
```

### Additional Components
- Expanded handler architecture with base and specialized handlers
- Content adaptation layer
- PDF-specific transformation utilities
- Modular file organization logic

## Dependencies
- google-genai: AI/LLM integration
- pydantic: Data validation
- python-dotenv: Configuration
- pillow: Image processing
- pdf2image: PDF handling
- PyPDF2: PDF metadata
- watchdog: File system monitoring
- PyYAML: Configuration files
- pytest: Testing framework
