# Active Context - Test Improvements

## Current Work
- Updated pipeline_test.py to handle non-deterministic AI-generated filenames
- Modified e2e_test.py to:
  - Handle unsupported file types gracefully
  - Add detailed output for debugging
  - Skip assertions for unsupported mime types
  - Add timeout handling for API calls

## Recent Changes
- Added support for skipping unsupported file types in tests
- Implemented detailed output for debugging test failures
- Added timeout handling to prevent indefinite hanging
- Updated test assertions to handle non-deterministic naming

## Known Issues
- Gemini API has limitations on supported mime types
- Some file types (.doc, .docx, .rtf, .xlsx) are not supported
- Test execution can time out due to API response times

## Next Steps
1. Add support for more file types in the API
2. Implement better error handling for unsupported files
3. Add retry logic for API calls
4. Improve test timeout handling
5. Add more detailed logging for debugging
