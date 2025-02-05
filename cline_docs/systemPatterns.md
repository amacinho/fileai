# System Patterns

## Pipeline Pattern
The system now uses a pipeline pattern for document processing:

```python
class DocumentPipeline:
    def extract_content(self) -> 'DocumentPipeline':
        # Extract content from document
        return self
        
    def categorize(self, api) -> 'DocumentPipeline':
        # Categorize document using API
        return self
        
    def move_to_destination(self, output_dir) -> 'DocumentPipeline':
        # Move file to final location
        return self
```

Benefits:
- Clear step-by-step processing
- Each step is independent and testable
- Easy to add new steps
- Better error handling
- State management through pipeline object

## Asset Pattern
Asset class serves as a temporary file container:
- Holds original file path
- Manages temporary processed content
- Tracks file type and MIME type
- Used for file operations

## Factory Pattern
Document handlers use factory pattern:
- BaseDocumentHandler defines interface
- Concrete handlers for each file type
- Factory method selects appropriate handler

## Strategy Pattern
Document categorization uses strategy pattern:
- Different LLM providers can be swapped
- Common interface for all providers
- Each provider implements its own categorization logic

## Observer Pattern
File system watching uses observer pattern:
- Watcher observes directory for changes
- Notifies processor when files are added
- Processor handles file processing asynchronously

## Data Flow
1. File Detection
   - Watcher observes file system
   - New files trigger processing

2. Content Extraction
   - Factory creates appropriate handler
   - Handler processes file content
   - Creates temporary files as needed

3. Categorization
   - API analyzes content
   - Returns metadata and category
   - Pipeline stores results

4. File Organization
   - Creates category directories
   - Handles duplicates
   - Moves files to final location

## Error Handling
- Each pipeline step can fail independently
- Errors are logged and contained
- Pipeline continues processing other files
- Temporary files cleaned up on failure

## Testing Strategy
- Unit tests for each component
- Integration tests for pipeline
- Mock responses for API calls
- Test fixtures for file operations
