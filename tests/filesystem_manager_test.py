import unittest
from unittest.mock import patch, mock_open
import sys
import os
from pathlib import Path

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fileai.filesystem_manager import FileSystemManager


class TestFileSystemManager(unittest.TestCase):
    def setUp(self):
        self.fs_manager = FileSystemManager()

    @patch('pathlib.Path.mkdir')
    @patch('shutil.move')
    def test_move_file(self, mock_move, mock_mkdir):
        source = Path("/test/source/file.txt")
        dest = Path("/test/dest/file.txt")
        
        result = self.fs_manager.move_file(source, dest)
        
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_move.assert_called_once_with(source, dest)
        self.assertEqual(result, dest)

    @patch('os.remove')
    def test_remove_file(self, mock_remove):
        # Test successful removal
        file_path = Path("/test/file.txt")
        self.fs_manager.remove_file(file_path)
        mock_remove.assert_called_once_with(file_path)
        
        # Test error handling
        mock_remove.side_effect = OSError("Test error")
        self.fs_manager.remove_file(file_path)  # Should not raise exception

    def test_compute_hash(self):
        # Test successful hash computation
        test_data = b"test content"
        mock_file = mock_open(read_data=test_data)
        
        with patch('builtins.open', mock_file):
            hash1 = self.fs_manager.compute_hash(Path("file1.txt"))
            hash2 = self.fs_manager.compute_hash(Path("file2.txt"))
            
            # Same content should produce same hash
            self.assertEqual(hash1, hash2)
            self.assertIsNotNone(hash1)
            self.assertEqual(len(hash1), 64)  # SHA-256 produces 64 char hex string
        
        # Test error handling
        with patch('builtins.open', side_effect=IOError()):
            hash_result = self.fs_manager.compute_hash(Path("nonexistent.txt"))
            self.assertIsNone(hash_result)

    def test_is_same_file(self):
        file1 = Path("/test/file1.txt")
        file2 = Path("/test/file2.txt")
        
        # Test files with same content
        with patch('pathlib.Path.exists', return_value=True):
            with patch.object(FileSystemManager, 'compute_hash', side_effect=["abc", "abc"]):
                self.assertTrue(self.fs_manager.is_same_file(file1, file2))
        
        # Test files with different content
        with patch('pathlib.Path.exists', return_value=True):
            with patch.object(FileSystemManager, 'compute_hash', side_effect=["abc", "def"]):
                self.assertFalse(self.fs_manager.is_same_file(file1, file2))
        
        # Test when hash computation fails
        with patch('pathlib.Path.exists', return_value=True):
            with patch.object(FileSystemManager, 'compute_hash', side_effect=[None, "abc"]):
                self.assertFalse(self.fs_manager.is_same_file(file1, file2))

        # Test when files don't exist
        with patch('pathlib.Path.exists', return_value=False):
            self.assertFalse(self.fs_manager.is_same_file(file1, file2))

    def test_read_text_content(self):
        test_content = "test content"
        mock_file = mock_open(read_data=test_content)
        
        # Test successful read
        with patch('builtins.open', mock_file):
            content = self.fs_manager.read_text_content(Path("test.txt"))
            self.assertEqual(content, test_content)
        
        # Test error handling
        with patch('builtins.open', side_effect=IOError()):
            content = self.fs_manager.read_text_content(Path("nonexistent.txt"))
            self.assertIsNone(content)

    def test_ensure_unique_path(self):
        base_path = Path("/test/file.txt")
        
        # Test when file doesn't exist
        with patch('pathlib.Path.exists', return_value=False):
            result = self.fs_manager.ensure_unique_path(base_path)
            self.assertEqual(result, base_path)
        
        # Test when file exists, should increment counter
        with patch('pathlib.Path.exists', side_effect=[True, True, False]):
            result = self.fs_manager.ensure_unique_path(base_path)
            self.assertEqual(result, Path("/test/file_2.txt"))
        
        # Test with multiple existing versions
        with patch('pathlib.Path.exists', side_effect=[True] * 5 + [False]):
            result = self.fs_manager.ensure_unique_path(base_path)
            self.assertEqual(result, Path("/test/file_5.txt"))


if __name__ == "__main__":
    unittest.main()
