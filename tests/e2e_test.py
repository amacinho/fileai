import os
import shutil
import subprocess
from pathlib import Path
import pytest
from fileai.file_operator import FileOperator

def print_directory_structure(path: Path, indent: int = 0):
    """Recursively print directory structure with indentation."""
    prefix = "  " * indent
    print(f"{prefix}{path.name}/")
    for item in path.iterdir():
        if item.is_dir():
            print_directory_structure(item, indent + 1)
        else:
            print(f"{prefix}  {item.name}")

@pytest.fixture
def temp_input_dir(tmp_path):
    """Create a temporary input directory and copy fixture files into it.""" 
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    # Copy all files from fixtures/input to temporary input directory
    fixtures_dir = Path(__file__).parent / "fixtures" / "input"
    for file_path in fixtures_dir.glob("*"):
        if file_path.is_file():
            shutil.copy2(file_path, input_dir)    
    yield input_dir
    shutil.rmtree(input_dir)

@pytest.fixture
def temp_output_dir(tmp_path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    yield output_dir
    shutil.rmtree(output_dir)

    
def test_end_to_end(temp_input_dir, temp_output_dir, request):
    """Test the complete file processing workflow."""
    project_root = Path(__file__).parent.parent
    main_script = project_root / "fileai" / "main.py"
    print(f"Command to run fileai: python {main_script} {temp_input_dir} {temp_output_dir} gemini")
    operator = FileOperator(temp_input_dir, temp_output_dir, "gemini")
    
    hash_to_file = {}
    supported_input_files = []
    unsupported_input_files = []
    supported_extensions = {'.txt', '.pdf', '.jpg', '.jpeg', '.html', '.png', '.docx', '.xlsx'}
    input_files = list(temp_input_dir.rglob("*"))
    for file in input_files:
        if file.is_file():
            if file.suffix.lower() in supported_extensions:
                file_hash = operator.compute_hash(file)
                hash_to_file[file_hash] = file
                supported_input_files.append(file)
            else:
                unsupported_input_files.append(file)
        
    print("\nInitial input directory structure:")
    print_directory_structure(temp_input_dir)
    
    print("\nInitial output directory structure:")
    print_directory_structure(temp_output_dir)
    result = subprocess.run(
        [
            "python",
            str(main_script),
            str(temp_input_dir),
            str(temp_output_dir),
            "gemini",
        ],
        capture_output=True,
        text=True,
        env={**os.environ}
    )
    
    # Print and check script execution
    print(f"Script stdout:\n{result.stdout}")
    print(f"Script stderr:\n{result.stderr}")
    
    print("\nAfter processing input directory structure:")
    print_directory_structure(temp_input_dir)

    print("\nAfter processing output directory structure:")
    print_directory_structure(temp_output_dir)

    assert result.returncode == 0, f"Script failed with error: {result.stderr}"
    
    # Only count files that are not in the unsupported directory
    output_files = [f for f in list(temp_output_dir.rglob("*")) 
                   if f.is_file() and "unsupported" not in str(f)]
    output_hashes = {operator.compute_hash(f): f for f in output_files if f.is_file()}

    assert len(output_files) == len(supported_input_files), (
        f"Expected {len(supported_input_files)} processed files, got {len(output_files)}"
    )

    for output_hash, output_file in output_hashes.items():
        assert output_hash in hash_to_file, (
            f"Output file {output_file.name} doesn't match any input file"
        )

    for input_hash in hash_to_file.keys():
        assert input_hash in output_hashes, (
            f"Input file {hash_to_file[input_hash].name} wasn't processed"
        )

    print("\nFile Mapping:")
    print("Processed files:")
    for hash_value in hash_to_file.keys():
        if hash_value in output_hashes:
            print(
                f"Input: {hash_to_file[hash_value].name} → "
                f"Output: {output_hashes[hash_value].name}"
            )

    print("\nUnsupported files (correctly skipped):")
    for file in unsupported_input_files:
        print(f"Skipped: {file.name}")

    # Optional: Additional verification that unsupported files weren't processed
    unsupported_file_hashes = {
        operator.compute_hash(f) for f in unsupported_input_files
    }
    processed_hashes = set(output_hashes.keys())
    assert not (unsupported_file_hashes & processed_hashes), (
        "Some unsupported files were incorrectly processed"
    )
