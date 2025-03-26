import unittest
from unittest.mock import patch, mock_open
from pathlib import Path

from fileai.file_system_operator import FileSystemOperator


class TestFileSystemOperator(unittest.TestCase):
    def setUp(self):
        self.input_base_path = Path("tests/fixtures/input")
        self.output_base_path = Path("tests/fixtures/output")
        self.file_system_operator = FileSystemOperator(self.input_base_path, self.output_base_path)
        # Mock directory manager for cleanup tests
        self.mock_directory_manager = patch('fileai.file_system_operator._DirectoryManager').start()
        self.file_system_operator.directory_manager = self.mock_directory_manager.return_value

    @patch('pathlib.Path.mkdir')
    @patch('shutil.move')
    def test_move_file(self, mock_move, mock_mkdir):
        source = self.input_base_path / "file.txt"
        dest = self.output_base_path / "file.txt"
        
        result = self.file_system_operator.move_file(source, dest)
        
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_move.assert_called_once_with(source, dest)
        self.assertEqual(result, dest)
        # Verify cleanup was called
        self.file_system_operator.directory_manager.cleanup_empty_dirs.assert_called_once_with(
            start_path=source.parent,
            stop_path=self.input_base_path
        )

    @patch('os.remove')
    def test_remove_file(self, mock_remove):
        # Test successful removal
        file_path = self.input_base_path / "file.txt"
        self.file_system_operator.remove_file(file_path)
        mock_remove.assert_called_once_with(file_path)
        # Verify cleanup was called
        self.file_system_operator.directory_manager.cleanup_empty_dirs.assert_called_once_with(
            start_path=file_path.parent,
            stop_path=self.input_base_path
        )
        
        # Test error handling
        mock_remove.side_effect = OSError("Test error")
        self.file_system_operator.remove_file(file_path)  # Should not raise exception
        # Verify cleanup not called on error
        self.assertEqual(self.file_system_operator.directory_manager.cleanup_empty_dirs.call_count, 1)

    def test_cleanup_after_operation(self):
        """Test the _cleanup_after_operation helper method"""
        test_path = self.input_base_path / "test.txt"
        
        # Test cleanup called for path under input base
        self.file_system_operator._cleanup_after_operation(test_path)
        self.file_system_operator.directory_manager.cleanup_empty_dirs.assert_called_once_with(
            start_path=test_path.parent,
            stop_path=self.input_base_path
        )
        
        # Test cleanup not called for path outside input base
        self.file_system_operator.directory_manager.reset_mock()
        outside_path = Path("/outside/path.txt")
        self.file_system_operator._cleanup_after_operation(outside_path)
        self.file_system_operator.directory_manager.cleanup_empty_dirs.assert_not_called()

    def test_compute_hash(self):
        # Test successful hash computation
        test_data = b"test content"
        mock_file = mock_open(read_data=test_data)
        
        with patch('builtins.open', mock_file):
            hash1 = self.file_system_operator.compute_hash(self.input_base_path / "file1.txt")
            hash2 = self.file_system_operator.compute_hash(self.input_base_path / "file2.txt")
            
            # Same content should produce same hash
            self.assertEqual(hash1, hash2)
            self.assertIsNotNone(hash1)
        # Test error handling
        with patch('builtins.open', side_effect=IOError()), patch('pathlib.Path.exists', return_value=False):
            hash_result = self.file_system_operator.compute_hash(self.input_base_path / "nonexistent.txt")
            self.assertIsNone(hash_result)

    @patch('pathlib.Path.stat')
    def test_is_same_file(self, mock_stat):
        file1 = self.input_base_path / "file1.txt"
        file2 = self.input_base_path / "file2.txt"
        
        # Mock stat to return same size for both files
        mock_stat.return_value.st_size = 1024
        
        # Test files with same content
        with patch('pathlib.Path.exists', return_value=True):
            with patch.object(FileSystemOperator, 'compute_hash', side_effect=["abc", "abc"]):
                self.assertTrue(self.file_system_operator.is_same_file(file1, file2))
        
        # Test files with different content
        with patch('pathlib.Path.exists', return_value=True):
            with patch.object(FileSystemOperator, 'compute_hash', side_effect=["abc", "def"]):
                self.assertFalse(self.file_system_operator.is_same_file(file1, file2))
        
        # Test when hash computation fails
        with patch('pathlib.Path.exists', return_value=True):
            with patch.object(FileSystemOperator, 'compute_hash', side_effect=[None, "abc"]):
                self.assertFalse(self.file_system_operator.is_same_file(file1, file2))

        # Test when files don't exist
        with patch('pathlib.Path.exists', return_value=False):
            self.assertFalse(self.file_system_operator.is_same_file(file1, file2))

        # Test when files have different sizes
        mock_stat.side_effect = [
            type('', (), {'st_size': 1024})(),  # file1 size
            type('', (), {'st_size': 2048})()   # file2 size
        ]
        with patch('pathlib.Path.exists', return_value=True):
            with patch.object(FileSystemOperator, 'compute_hash', side_effect=["abc", "abc"]):
                self.assertFalse(self.file_system_operator.is_same_file(file1, file2))

    def test_read_text_content(self):
        test_content = "test content"
        mock_file = mock_open(read_data=test_content)
        
        # Test successful read
        with patch('builtins.open', mock_file):
            content = self.file_system_operator.read_text_content(self.input_base_path / "test.txt")
            self.assertEqual(content, test_content)
        
        # Test error handling
        with patch('builtins.open', side_effect=OSError()):
            with self.assertRaises(OSError):
                self.file_system_operator.read_text_content(self.input_base_path / "nonexistent.txt")

    def test_ensure_unique_path(self):
        base_path = Path("/test/file.txt")
        
        # Test when file doesn't exist
        with patch('pathlib.Path.exists', return_value=False):
            result = self.file_system_operator.ensure_unique_path(base_path)
            self.assertEqual(result, base_path)
        
        # Test when file exists, should increment counter
        with patch('pathlib.Path.exists', side_effect=[True, True, False]):
            result = self.file_system_operator.ensure_unique_path(base_path)
            self.assertEqual(result, Path("/test/file_2.txt"))
        
        # Test with multiple existing versions
        with patch('pathlib.Path.exists', side_effect=[True] * 5 + [False]):
            result = self.file_system_operator.ensure_unique_path(base_path)
            self.assertEqual(result, Path("/test/file_5.txt"))


if __name__ == "__main__":
    unittest.main()
