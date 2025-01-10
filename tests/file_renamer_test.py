import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add parent directory to Python path to import FileRenamer
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fileai.file_renamer import FileRenamer


class TestFileRenamer(unittest.TestCase):
    def setUp(self):
        self.mock_api = Mock()
        self.renamer = FileRenamer(self.mock_api)

    def test_ensure_output_structure(self):
        with patch('fileai.file_renamer.Path') as mock_path:
            # Setup mock path instance
            mock_path_instance = Mock()
            mock_category_dir = Mock()
            mock_path_instance.__truediv__ = Mock(return_value=mock_category_dir)
            mock_path.return_value = mock_path_instance

            # Create a new FileRenamer instance to trigger ensure_output_structure
            FileRenamer(self.mock_api)

            # Verify Path was called with 'output'
            mock_path.assert_called_once_with('output')

            # Expected categories
            expected_categories = [
                'medical', 'financial', 'travel', 'personal',
                'technical', 'legal', 'receipts', 'misc'
            ]

            # Verify each category directory was created
            self.assertEqual(mock_path_instance.__truediv__.call_count, len(expected_categories))
            mock_category_dir.mkdir.assert_has_calls(
                [unittest.mock.call(parents=True, exist_ok=True)] * len(expected_categories)
            )

            # Verify the categories were created in the correct order
            calls = mock_path_instance.__truediv__.call_args_list
            for i, category in enumerate(expected_categories):
                self.assertEqual(calls[i][0][0], category)


if __name__ == '__main__':
    unittest.main()
