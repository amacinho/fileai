import os
import shutil
import subprocess
from pathlib import Path
import pytest

@pytest.fixture
def temp_input_dir(tmp_path):
    """Create a temporary input directory and copy fixture files into it."""
    # Create temporary input directory
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    
    # Copy all files from fixtures/input to temporary input directory
    fixtures_dir = Path(__file__).parent / "fixtures" / "input"
    for file_path in fixtures_dir.glob("*"):
        if file_path.is_file():
            shutil.copy2(file_path, input_dir)
    
    yield input_dir
    
    # Cleanup: Remove temporary input directory and its contents
    shutil.rmtree(input_dir)

def test_end_to_end(temp_input_dir):
    """Test the complete file processing workflow."""
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    
    # Run the main script with the temporary input directory
    main_script = project_root / "fileai" / "main.py"
    output_dir = project_root / "output"
    result = subprocess.run(
        [
            "python",
            str(main_script),
            str(temp_input_dir),  # input_path
            str(output_dir),      # output_path
            "gemini",             # api_type
        ],
        capture_output=True,
        text=True,
        env={**os.environ}  # Use current environment variables (including API keys)
    )
    
    # Print and check script execution
    print(f"Script stdout:\n{result.stdout}")
    print(f"Script stderr:\n{result.stderr}")
    assert result.returncode == 0, f"Script failed with error: {result.stderr}"
    
    # Define expected output directories
    output_dirs = [
        "output/financial",
        "output/personal",
        "output/misc",
        "output/technical",
        "output/legal",
        "output/medical",
        "output/receipts",
        "output/travel"
    ]
    
    # Verify output directories exist
    for dir_path in output_dirs:
        output_dir = project_root / dir_path
        assert output_dir.exists(), f"Output directory {dir_path} does not exist"
    
    # Verify files have been moved and categorized
    # Note: We check for the presence of files with the original names
    # In a real scenario, the files might be renamed by the categorizer
    expected_files = {
        "output/financial": ["cv.pdf"],
        "output/personal": ["cv.html"],
        "output/misc": [
            "cv.jpeg",
            "doc1.doc",
            "doc1.docx",
            "doc1.odt",
            "doc1.rtf",
            "doc1.xlsx",
            "test.txt"
        ],
        "output/technical": ["cv.png"]
    }
    
    for dir_path, files in expected_files.items():
        output_dir = project_root / dir_path
        for file_name in files:
            # Check if any file in the directory starts with the original name
            # (ignoring potential renaming)
            found = False
            for existing_file in output_dir.glob("*"):
                if existing_file.name.startswith(file_name.split(".")[0]):
                    found = True
                    break
            assert found, f"No file matching {file_name} found in {dir_path}"
    
    # Verify input directory is empty (all files have been moved)
    remaining_files = list(temp_input_dir.glob("*"))
    assert len(remaining_files) == 0, f"Input directory still contains files: {remaining_files}"
