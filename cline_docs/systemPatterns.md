# System Patterns

## Core Components

1. **Main Workflow**
   - Watcher monitors input directory
   - Pipeline processes files through stages
   - Categorizer classifies documents
   - FileOperator handles file system operations

2. **Document Processing**
   - Handlers for different file types
   - Temporary file creation
   - Content extraction and conversion
   - Metadata extraction

3. **API Integration**
   - Gemini API implementation
   - Rate limiting
   - Structured response handling

4. **File System Management**
   - Directory structure creation
   - File movement and copying
   - Empty directory cleanup
   - Path validation

## Architectural Patterns

1. **Pipeline Pattern**
   - Document processing as a series of stages
   - State management through PipelineState
   - Clear separation of concerns

2. **Factory Pattern**
   - Handler selection based on file type
   - Extensible handler system

3. **Observer Pattern**
   - File system monitoring
   - Event-driven processing

4. **Rate Limiting**
   - API call throttling
   - Queue-based implementation
   - Automatic wait calculation

## Error Handling

1. Comprehensive logging
2. Graceful fallbacks
3. Input validation
4. Resource cleanup
