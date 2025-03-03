# import pytest
# import pathlib as path
# import zipfile
# import py7zr
# import tarfile
# import datetime
# from Utility import (
#     is_corrupted,
#     is_archive_corrupted,
#     move_file_with_retry,
#     FileHandler
# )
#
#
# @pytest.fixture
# def sample_files(tmp_path):
#     """Creates temporary test files for unit testing."""
#     valid_txt = tmp_path / "valid.txt"
#     valid_txt.write_text("This is a test file.")
#
#     corrupt_txt = tmp_path / "corrupt.txt"
#     corrupt_txt.touch()  # Empty file (corrupt)
#
#     temp_file = tmp_path / "~$tempfile.docx"
#     temp_file.write_text("This should be ignored.")
#
#     valid_zip = tmp_path / "valid.zip"
#     with zipfile.ZipFile(valid_zip, "w") as zip_ref:
#         zip_ref.writestr("inside.txt", "This is inside the zip.")  # Valid ZIP
#
#     corrupt_zip = tmp_path / "corrupt.zip"
#     corrupt_zip.write_text("Not a real zip file")  # Invalid ZIP
#
#     return {
#         "valid": valid_txt,
#         "corrupt": corrupt_txt,
#         "temp": temp_file,
#         "valid_zip": valid_zip,
#         "corrupt_zip": corrupt_zip
#     }
#
#
# def test_is_corrupted(sample_files):
#     """Test detection of corrupted files."""
#     assert is_corrupted(sample_files["valid"]) == False
#     assert is_corrupted(sample_files["corrupt"]) == True
#
#
# def test_is_archive_corrupted(sample_files):
#     """Test detection of corrupted archives."""
#     assert is_archive_corrupted(sample_files["valid_zip"]) == False  # Valid archive
#     assert is_archive_corrupted(sample_files["corrupt_zip"]) == True  # Corrupt archive
#
#
# def test_move_file_with_retry(tmp_path, sample_files):
#     """Test file moving with retry logic."""
#     dest_path = tmp_path / "moved"
#     dest_path.mkdir()
#
#     move_file_with_retry({"Path": sample_files["valid"]}, dest_path)
#     assert (dest_path / "valid.txt").exists()
#
#
# def test_parse_file(sample_files):
#     """Test if FileHandler._parse_file() correctly filters files."""
#     file_types = {"Text": [".txt"], "Archive": [".zip"]}  # Ensure valid type mapping
#     file_handler = FileHandler("/dummy/source", file_types, "/dummy/log", [], file_types)
#     parsed = file_handler._parse_file(sample_files.values())
#
#     assert parsed is not None, "Parsed files should not be None"
#     assert len(parsed) == 2, f"Expected 2 file, found {len(parsed)}"
#     parsed_names = {file["File name"] for file in parsed}
#     assert "valid" in parsed_names, "Missing valid.txt in parsed files"
#     assert "valid" in parsed_names, "Missing valid.zip in parsed files"
#
#
# def test_handle(tmp_path, sample_files):
#     """Test if FileHandler.handle() processes and moves files and extracts archives correctly."""
#     file_types = {"Text": [".txt"], "Archive": [".zip"]}  # Ensure proper file type mapping
#     file_handler = FileHandler(str(tmp_path), {"Text":tmp_path / "Text","Archive":tmp_path}, "/dummy/log", [], file_types)
#
#     # Process the valid text file and archive
#     file_handler.handle([sample_files["valid"], sample_files["valid_zip"]])
#
#     # Ensure date-based directory exists
#     current_date = datetime.datetime.now().strftime("%d-%m-%Y")
#
#     # Correct text file path
#     text_file_dest = tmp_path / "Text" / current_date / "valid.txt"
#     assert text_file_dest.exists(), f"File was not moved to {text_file_dest}"
#
#     archive_name = sample_files["valid_zip"].stem  # Folder name should match archive name
#     extracted_folder = tmp_path / archive_name
#     extracted_file = extracted_folder / "inside.txt"
#
#     assert extracted_file.exists(), f"Archive was not extracted correctly to {extracted_folder}"

import pytest
import pathlib as path
import zipfile
import py7zr
import tarfile
import datetime
import os
import time
from Utility import (
    is_corrupted,
    is_archive_corrupted,
    move_file_with_retry,
    FileHandler
)


@pytest.fixture
def sample_files(tmp_path):
    """Creates temporary test files for unit testing."""
    valid_txt = tmp_path / "valid.txt"
    valid_txt.write_text("This is a test file.")

    corrupt_txt = tmp_path / "corrupt.txt"
    corrupt_txt.touch()  # Empty file (corrupt)

    temp_file = tmp_path / "~$tempfile.docx"
    temp_file.write_text("This should be ignored.")

    valid_zip = tmp_path / "valid.zip"
    with zipfile.ZipFile(valid_zip, "w") as zip_ref:
        zip_ref.writestr("inside.txt", "This is inside the zip.")  # Valid ZIP

    corrupt_zip = tmp_path / "corrupt.zip"
    corrupt_zip.write_text("Not a real zip file")  # Invalid ZIP

    empty_zip = tmp_path / "empty.zip"
    with zipfile.ZipFile(empty_zip, "w") as zip_ref:
        pass  # Create an empty zip file

    no_ext_file = tmp_path / "no_extension"
    no_ext_file.write_text("This file has no extension.")

    unsupported_file = tmp_path / "unsupported.xyz"
    unsupported_file.write_text("Unsupported file type.")

    return {
        "valid": valid_txt,
        "corrupt": corrupt_txt,
        "temp": temp_file,
        "valid_zip": valid_zip,
        "corrupt_zip": corrupt_zip,
        "empty_zip": empty_zip,
        "no_extension": no_ext_file,
        "unsupported": unsupported_file
    }


def test_is_corrupted(sample_files):
    """Test detection of corrupted files."""
    assert is_corrupted(sample_files["valid"]) == False
    assert is_corrupted(sample_files["corrupt"]) == True


def test_is_corrupted_edge_cases(tmp_path):
    """Test edge cases for is_corrupted()."""
    null_byte_file = tmp_path / "null_bytes.txt"
    null_byte_file.write_bytes(b"\x00" * 10)  # Write only null bytes
    assert is_corrupted(null_byte_file) == False, "File with null bytes should not be corrupt"


def test_is_archive_corrupted(sample_files):
    """Test detection of corrupted archives."""
    assert is_archive_corrupted(sample_files["valid_zip"]) == False  # Valid archive
    assert is_archive_corrupted(sample_files["corrupt_zip"]) == True  # Corrupt archive


def test_is_archive_corrupted_edge_cases(sample_files):
    """Test edge cases for is_archive_corrupted()."""
    assert is_archive_corrupted(sample_files["empty_zip"]) == False, "Empty zip should not be corrupt"


def test_parse_file(sample_files):
    """Test if FileHandler._parse_file() correctly filters files."""
    file_types = {"Text": [".txt"], "Archive": [".zip"]}  # Ensure valid type mapping
    file_handler = FileHandler("/dummy/source", file_types, "/dummy/log", [], file_types)
    parsed = file_handler._parse_file(sample_files.values())

    assert parsed is not None, "Parsed files should not be None"
    assert len(parsed) == 2, f"Expected 2 files, found {len(parsed)}"


def test_parse_file_edge_cases(sample_files, tmp_path):
    """Test if _parse_file() ignores unsupported and extension-less files."""
    file_types = {"Text": [".txt"], "Archive": [".zip"]}
    file_handler = FileHandler("/dummy/source", file_types, "/dummy/log", [], file_types)
    parsed = file_handler._parse_file(
        [sample_files["valid"], sample_files["no_extension"], sample_files["unsupported"]])

    assert len(parsed) == 1, f"Expected 1 parsed file, found {len(parsed)}"
    assert parsed[0]["File name"] == "valid", "Expected 'valid.txt' to be parsed"


def test_move_file_with_retry(tmp_path, sample_files):
    """Test file moving with retry logic."""
    dest_path = tmp_path / "moved"
    dest_path.mkdir()

    move_file_with_retry({"Path": sample_files["valid"]}, dest_path)
    assert (dest_path / "valid.txt").exists()


def test_handle(tmp_path, sample_files):
    """Test if FileHandler.handle() processes and moves files correctly."""
    file_types = {"Text": [".txt"], "Archive": [".zip"]}  # Ensure proper file type mapping
    file_handler = FileHandler(str(tmp_path), {"Text": tmp_path / "Text", "Archive": tmp_path}, "/dummy/log", [],
                               file_types)

    file_handler.handle([sample_files["valid"], sample_files["valid_zip"]])

    current_date = datetime.datetime.now().strftime("%d-%m-%Y")

    text_file_dest = tmp_path / "Text" / current_date / "valid.txt"
    assert text_file_dest.exists(), f"File was not moved to {text_file_dest}"

    archive_name = sample_files["valid_zip"].stem
    extracted_folder = tmp_path / archive_name
    extracted_file = extracted_folder / "inside.txt"
    assert extracted_file.exists(), f"Archive was not extracted correctly to {extracted_folder}"


def test_handle_existing_file(tmp_path, sample_files):
    """Test if handle() correctly processes files that already exist in the destination."""
    file_types = {"Text": [".txt"]}
    file_handler = FileHandler(str(tmp_path), {"Text": tmp_path / "Text"}, "/dummy/log", [], file_types)

    file_handler.handle([sample_files["valid"]])
    file_handler.handle([sample_files["valid"]])

    dest_folder = tmp_path / "Text" / datetime.datetime.now().strftime("%d-%m-%Y")
    assert (dest_folder / "valid.txt").exists(), "File should exist even after reprocessing"
