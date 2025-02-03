import pytest
from pathlib import Path
from fileai.directory_manager import DirectoryManager
from fileai.config import FOLDERS

@pytest.fixture
def temp_base_dir(tmp_path):
    """Create a temporary base directory for testing."""
    return tmp_path

@pytest.fixture
def directory_manager(temp_base_dir):
    """Create a DirectoryManager instance with temporary base directory."""
    return DirectoryManager(temp_base_dir)

def test_ensure_category_structure(directory_manager, temp_base_dir):
    """Test that ensure_category_structure creates all required directories."""
    directory_manager.ensure_category_structure()
    
    # Verify all category directories were created
    for folder_name, _ in FOLDERS:
        category_dir = temp_base_dir / folder_name
        assert category_dir.exists()
        assert category_dir.is_dir()

def test_get_category_path_valid(directory_manager):
    """Test get_category_path with valid category."""
    # Use first category from FOLDERS for test
    test_category = FOLDERS[0][0]
    category_path = directory_manager.get_category_path(test_category)
    
    assert category_path == directory_manager.base_dir / test_category

def test_get_category_path_invalid(directory_manager):
    """Test get_category_path with invalid category defaults to misc."""
    invalid_category = "nonexistent_category"
    category_path = directory_manager.get_category_path(invalid_category)
    
    assert category_path == directory_manager.base_dir / "misc"

def test_cleanup_empty_dirs(directory_manager, temp_base_dir):
    """Test cleanup_empty_dirs removes empty directories."""
    # Create a nested directory structure
    nested_dir = temp_base_dir / "parent" / "child" / "grandchild"
    nested_dir.mkdir(parents=True)
    
    # Create a file in parent to prevent its deletion
    parent_file = temp_base_dir / "parent" / "file.txt"
    parent_file.write_text("test content")
    
    # Clean up from grandchild
    directory_manager.cleanup_empty_dirs(nested_dir, temp_base_dir)
    
    # Verify grandchild and child are removed, but parent remains
    assert not (temp_base_dir / "parent" / "child" / "grandchild").exists()
    assert not (temp_base_dir / "parent" / "child").exists()
    assert (temp_base_dir / "parent").exists()
    assert parent_file.exists()

def test_is_empty_dir(directory_manager, temp_base_dir):
    """Test _is_empty_dir correctly identifies empty directories."""
    # Create empty directory
    empty_dir = temp_base_dir / "empty"
    empty_dir.mkdir()
    
    # Create non-empty directory
    nonempty_dir = temp_base_dir / "nonempty"
    nonempty_dir.mkdir()
    (nonempty_dir / "file.txt").write_text("test content")
    
    assert directory_manager._is_empty_dir(empty_dir)
    assert not directory_manager._is_empty_dir(nonempty_dir)
    assert not directory_manager._is_empty_dir(temp_base_dir / "nonexistent")

def test_get_relative_path(directory_manager, temp_base_dir):
    """Test get_relative_path returns correct relative paths."""
    # Create a test file
    test_file = temp_base_dir / "test.txt"
    test_file.write_text("test content")
    
    # Test with path inside base directory
    relative_path = directory_manager.get_relative_path(test_file)
    assert relative_path == Path("test.txt")
    
    # Test with path outside base directory
    outside_path = Path("/some/other/path")
    assert directory_manager.get_relative_path(outside_path) is None
