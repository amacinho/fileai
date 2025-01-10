import unittest
from unittest.mock import Mock, patch, mock_open, call
import sys
import os
from pathlib import Path

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fileai.file_organizer import FileOrganizer
from fileai.api import GeminiAPI


class TestFileOrganizer(unittest.TestCase):
    def setUp(self):
        self.mock_api = Mock(spec=GeminiAPI)
        self.input_path = Path("/test/input")
        self.output_path = Path("/test/output")
        self.organizer = FileOrganizer(self.input_path, self.output_path, self.mock_api)
        self.organizer._move_file = Mock()
        self.organizer._remove_file = Mock()

    def test_is_processable_file(self):
        # Test supported extensions
        self.assertTrue(self.organizer.is_processable_file(Path("test.pdf")))
        self.assertTrue(self.organizer.is_processable_file(Path("test.jpg")))
        self.assertTrue(self.organizer.is_processable_file(Path("test.txt")))

        # Test unsupported extensions
        self.assertFalse(self.organizer.is_processable_file(Path("test.exe")))
        self.assertFalse(self.organizer.is_processable_file(Path("test.zip")))

    def test_file_type_checks(self):
        # Test image files
        self.assertTrue(self.organizer.is_image(Path("test.jpg")))
        self.assertTrue(self.organizer.is_image(Path("test.png")))
        self.assertFalse(self.organizer.is_image(Path("test.pdf")))

        # Test text files
        self.assertTrue(self.organizer.is_text(Path("test.txt")))
        self.assertFalse(self.organizer.is_text(Path("test.jpg")))

        # Test PDF files
        self.assertTrue(self.organizer.is_pdf(Path("test.pdf")))
        self.assertFalse(self.organizer.is_pdf(Path("test.txt")))

        # Test doc files
        self.assertTrue(self.organizer.is_doc(Path("test.doc")))
        self.assertTrue(self.organizer.is_doc(Path("test.docx")))
        self.assertFalse(self.organizer.is_doc(Path("test.pdf")))

    @patch("builtins.open", new_callable=mock_open, read_data="test content")
    def test_read_text_content(self, mock_file):
        content = self.organizer.read_text_content(Path("test.txt"))
        self.assertEqual(content, "test content")
        mock_file.assert_called_once_with(Path("test.txt"), "r", encoding="utf-8")

    def test_compute_hash(self):
        # Test identical files have same hash
        with patch(
            "builtins.open", new_callable=mock_open, read_data=b"test data"
        ):
            file1_hash = self.organizer.compute_hash(Path("file1.txt"))

        with patch(
            "builtins.open", new_callable=mock_open, read_data=b"test data"
        ):
            file2_hash = self.organizer.compute_hash(Path("file2.txt"))

        self.assertEqual(file1_hash, file2_hash)

        # Test different content produces different hashes
        with patch(
            "builtins.open", new_callable=mock_open, read_data=b"different data"
        ):
            file3_hash = self.organizer.compute_hash(Path("file3.txt"))

        self.assertNotEqual(file1_hash, file3_hash)

        # Test large file handling (simulate reading in chunks)
        large_data = b"x" * 1024 * 400  # 400KB of data
        mock_large_file = mock_open(read_data=large_data)
        with patch("builtins.open", mock_large_file):
            large_file_hash = self.organizer.compute_hash(Path("large_file.txt"))

        self.assertIsNotNone(large_file_hash)
        self.assertEqual(
            len(large_file_hash), 64
        )  # SHA-256 produces 64 character hex string

        # Test error handling
        with patch("builtins.open", side_effect=IOError()):
            error_hash = self.organizer.compute_hash(Path("nonexistent.txt"))
        self.assertIsNone(error_hash)

    def test_extract_content(self):
        # Test PDF extraction
        pdf_path = Path("test.pdf")
        content, asset = self.organizer._extract_content(pdf_path)
        self.assertEqual(content, "")
        self.assertEqual(asset.mime_type, "application/pdf")
        self.assertEqual(asset.path, str(pdf_path))

        # Test image extraction
        img_path = Path("test.jpg")
        content, asset = self.organizer._extract_content(img_path)
        self.assertEqual(content, "")
        self.assertEqual(asset.mime_type, "image/jpg")
        self.assertEqual(asset.path, str(img_path))

        # Test text extraction
        with patch.object(
            FileOrganizer, "read_text_content", return_value="test content"
        ):
            content, asset = self.organizer._extract_content(Path("test.txt"))
            self.assertEqual(content, "test content")
            self.assertIsNone(asset)

        # Test doc extraction
        with self.assertRaises(NotImplementedError):
            self.organizer._extract_content(Path("test.doc"))

    def test_file_versioning_and_deduplication(self):
        # Mock dependencies
        mock_hash1 = "1234"
        mock_hash2 = "5678"

        # Mock the file_renamer
        self.organizer.file_renamer = Mock()
        self.organizer.file_renamer.categorize_file.return_value = (
            "document",
            "category",
        )
        # Setup test files
        input_file = Path("/test/input/document.pdf")
        output_base = self.output_path / "category"
        output_file = output_base / "document.pdf"
        output_file_v1 = output_base / "document_1.pdf"
        output_file_v2 = output_base / "document_2.pdf"

        # Test case 1: New file (no existing file)
        with patch("pathlib.Path.exists", return_value=False):
            with patch.object(FileOrganizer, "compute_hash") as mock_hash:
                self.organizer.organize_file(input_file)
                self.organizer._move_file.assert_called_with(
                    current_file_name=input_file, new_file_name=output_file
                )
                mock_hash.assert_not_called()
                self.organizer._move_file.reset_mock()

        # Test case 2: File exists but has different content
        with patch("pathlib.Path.exists", side_effect=[True, False]):
            with patch.object(
                FileOrganizer, "compute_hash", side_effect=[mock_hash1, mock_hash2]
            ) as mock_hash:
                self.organizer.organize_file(input_file)
                self.organizer._move_file.assert_called_with(
                    current_file_name=input_file, new_file_name=output_file_v1
                )
                mock_hash.assert_has_calls([call(output_file), call(input_file)])
                self.organizer._move_file.reset_mock()

        # Test case 3: File exists with identical content (should be skipped)
        with patch("pathlib.Path.exists", return_value=True):
            with patch.object(
                FileOrganizer, "compute_hash", side_effect=[mock_hash1, mock_hash1]
            ) as mock_hash:
                self.organizer.organize_file(input_file)
                self.organizer._move_file.assert_not_called()
                mock_hash.assert_has_calls(
                    [call(output_file), call(input_file)]
                )
                self.organizer._remove_file.assert_called_once_with(input_file)
                self.organizer._remove_file.reset_mock()

        # Test case 4: Multiple versions exist, should increment
        with patch("pathlib.Path.exists", side_effect=[True, True, False]):
            with patch.object(
                FileOrganizer, "compute_hash", side_effect=["1", "2", "1", "3"]
            ) as mock_hash:
                self.organizer.organize_file(input_file)
                self.organizer._move_file.assert_called_with(
                    current_file_name=input_file, new_file_name=output_file_v2
                )

    def test_complex_versioning_scenarios(self):
        # Mock dependencies
        self.organizer.file_renamer = Mock()
        self.organizer.file_renamer.categorize_file.return_value = (
            "document",
            "category",
        )

        input_file = Path("/test/input/document.pdf")
        output_base = self.output_path / "category"
        # Test case 1: Handle gaps in version numbers
        exists_side_effects = {
            str(output_base / "document.pdf"): True,
            str(output_base / "document_1.pdf"): True,
            str(output_base / "document_2.pdf"): False,
            str(output_base / "document_3.pdf"): True,
            str(output_base / "document_4.pdf"): False,
        }

        with patch(
            "pathlib.Path.exists",
            lambda self: exists_side_effects.get(str(self), False),
        ):
            with patch.object(
                FileOrganizer,
                "compute_hash",
                side_effect=["1234", "5678", "1234", "9101112"],
            ):
                self.organizer.organize_file(input_file)
                self.organizer._move_file.assert_called_with(
                    current_file_name=input_file,
                    new_file_name=output_base / "document_2.pdf",
                )
            self.organizer._move_file.reset_mock()

        # Test case 2: Handle very large version numbers
        exists_side_effects = {
            f"{output_base}/document_{i}.pdf": True for i in range(100)
        }
        exists_side_effects[f"{output_base}/document.pdf"] = True
        exists_side_effects[f"{output_base}/document_100.pdf"] = False

        with patch(
            "pathlib.Path.exists",
            lambda self: exists_side_effects.get(str(self), False),
        ):
            with patch.object(
                FileOrganizer,
                "compute_hash",
                side_effect=[str(x) for x in range(201)],
            ):
                self.organizer.organize_file(input_file)
                self.organizer._move_file.assert_called_with(
                    current_file_name=input_file,
                    new_file_name=output_base / "document_100.pdf",
                )

    @patch.object(FileOrganizer, "_extract_content")
    def test_organize_file(self, mock_extract):
        # Setup mocks
        mock_extract.return_value = ("test content", None)
        self.organizer.file_renamer = Mock()
        self.organizer.file_renamer.categorize_file.return_value = (
            "new_name",
            "category",
        )

        # Test successful organization
        file_path = Path("/test/input/test.txt")
        self.organizer.organize_file(file_path)

        self.organizer.file_renamer.categorize_file.assert_called_once()
        self.organizer._move_file.assert_called_once()

        # Reset mocks for .DS_Store test
        mock_extract.reset_mock()
        self.organizer._move_file.reset_mock()

        # Test with .DS_Store file
        ds_store = Path("/test/input/.DS_Store")
        self.organizer.organize_file(ds_store)
        # Verify no processing occurred
        mock_extract.assert_not_called()
        self.organizer._move_file.assert_not_called()

    @patch.object(Path, "rglob")
    @patch.object(Path, "is_dir")
    @patch.object(Path, "is_relative_to")
    def test_organize_directory(self, mock_relative_to, mock_is_dir, mock_rglob):
        # Setup mock files
        mock_files = [
            Path("/test/input/file1.txt"),
            Path("/test/input/file2.pdf"),
            Path("/test/input/file3.jpg"),
        ]
        mock_rglob.return_value = mock_files
        mock_is_dir.return_value = False
        mock_relative_to.return_value = False

        # Test directory organization
        with patch.object(FileOrganizer, "organize_file") as mock_organize:
            self.organizer.organize_directory()
            self.assertEqual(mock_organize.call_count, len(mock_files))

        # Test with directory in path
        mock_is_dir.return_value = True
        with patch.object(FileOrganizer, "organize_file") as mock_organize:
            self.organizer.organize_directory()
            mock_organize.assert_not_called()


if __name__ == "__main__":
    unittest.main()
