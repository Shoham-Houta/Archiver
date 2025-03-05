import os
import pathlib as path
import datetime as dt
import logging
import tarfile
import shutil
import time
import tracemalloc
import functools
import platform
import py7zr
import zipfile
import concurrent.futures
from py7zr.exceptions import Bad7zFile

if platform.system() == "Windows":
    import msvcrt  # Windows file locking
else:
    import fcntl  # Linux/macOS file locking


def performance_debug(func):
    """
    Decorator to measure execution time and memory usage of a function.
    Logs the results for debugging performance issues.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Start tracking memory
        tracemalloc.start()

        # Start tracking execution time
        start_time = time.perf_counter()

        # Execute the function
        result = func(*args, **kwargs)

        # Stop tracking execution time
        end_time = time.perf_counter()

        # Get memory usage
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Print performance report
        print(f"[PERFORMANCE] {func.__name__}:")
        print(f"    Execution Time: {end_time - start_time:.6f} seconds")
        print(
            f"    Memory Usage: {current / 1024:.2f} KB (Peak: {peak / 1024:.2f} KB)")

        return result

    return wrapper


def is_locked(file_path):
    try:
        with open(file_path, "a+") as f:
            if platform.system() == "Windows":
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return False  # File is NOT locked
    except (PermissionError, BlockingIOError, OSError):
        return True  # File is locked


def move_file_with_retry(file, destination, retries=5, delay=2):
    """Tries to move a file, retrying if it's locked (e.g., by antivirus)."""
    for attempt in range(retries):
        if not is_locked(file["Path"]):  # Check if file is locked
            try:
                shutil.move(file["Path"], destination)
                logging.info(f"{file['File name']} ---> {destination}")
                return  # Success
            except PermissionError:
                logging.warning(f"Permission denied: {file['Path']}. Retrying...")
            except FileNotFoundError:
                logging.error(f"Error: {file['Path']} not found. Skipping...")
                return
            except Exception as e:
                logging.error(
                    f"Unexpected error ({type(e).__name__}) in file {file['Path']}: {e}. Skipping...")
                return
        else:
           logging.warning(
                f"Attempt #{attempt+1}:\nFile {file['File name']} is locked (likely by antivirus). Retrying in {delay} seconds...")
        time.sleep(delay)  # Wait before retrying
    logging.error(
        f"Skipping {file['File name']}: Still locked after {retries} attempts.")


def is_corrupted(file_path):

    file_path_obj = path.Path(file_path)
    if not file_path_obj.exists():
        return True  # File does not exist
    if file_path_obj.stat().st_size == 0:
        return True  # File is empty

    try:
        with open(file_path_obj, 'rb') as f:
            f.read(1024)
        return False  # File is not corrupted
    except (IOError, OSError):
        return True  # File is corrupted

def is_archive_empty(file_path):
    """Check if an archive is empty before processing."""
    try:
        file_path = path.Path(file_path)
        if file_path.suffix == ".zip":
            with zipfile.ZipFile(file_path, "r") as zip_ref:
                return len(zip_ref.namelist()) == 0
        elif file_path.suffix == ".7z":
            with py7zr.SevenZipFile(file_path, "r") as archive:
                return len(archive.getnames()) == 0
        elif file_path.suffix in [".tar", ".gz", ".bz2"]:
            with tarfile.open(file_path, "r:*") as archive:
                return len(archive.getnames()) == 0
        return False  # If not an archive, assume not empty
    except Exception:
        return True  # If there's an error, assume it's empty


def is_archive_corrupted(file_path):
    file_path_obj = path.Path(file_path)
    try:
        if file_path_obj.suffix == ".zip":
            with zipfile.ZipFile(file_path_obj) as zip_ref:
                if zip_ref.testzip() is not None:
                    return True  # Archive is corrupted
        elif file_path_obj.suffix == ".7z":
            with py7zr.SevenZipFile(file_path_obj, mode='r') as archive:
                if archive.test():
                    return True  # Archive is corrupted
        elif file_path_obj.suffix in {".tar", ".gz", ".bz2"}:
            with tarfile.open(file_path_obj, 'r:*') as f:
                f.getmembers()
        return False
    except (zipfile.BadZipFile, Bad7zFile, tarfile.TarError) as e:
        # Archive is corrupted
        logging.warning(f"Archive {file_path_obj} is corrupted ({type(e).__name__}).")
        return True
    except Exception as e:
        logging.error(
            f"Error checking archive {file_path_obj} ({type(e).__name__}): {e}")
        return True  # Archive is corrupted


class FileHandler:
    def __init__(self, source, dest_paths, logger_output, logger_lvls, types, delete_archives=False):
        self._source = path.Path(source)
        self._dest: dict = dest_paths
        self._logger_output = path.Path(logger_output)
        self._logger_levels: list = logger_lvls
        self._types: dict = types
        self.archive_handler = ArchiveHandler(
            dest_paths, delete_after_extract=delete_archives)

        self._init_logger()

    def _init_logger(self):

        self.logger = logging.getLogger("FileHandler")

        level_mapping = {
            "DEBUG": logging.DEBUG,
            "INFO":logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR
        }
        # Select the lowest logging level from the provided list
        selected_level = min([level_mapping.get(level.upper(), logging.INFO) for level in self._logger_levels])

        self.logger.setLevel(selected_level)

        log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)
        self.logger.addHandler(console_handler)

        # File handler
        log_file = self._logger_output / ".archiver.log"
        file_handler = logging.FileHandler(log_file, mode="a")
        file_handler.setFormatter(log_formatter)
        self.logger.addHandler(file_handler)

        self.logger.info(
            f"Logging initialized with levels: {', '.join(self._logger_levels)} (Using: {logging.getLevelName(selected_level)})")

    @property
    def source(self):
        return self._source

    def _parse_file(self, files):
        parsed_files = []
        for file in files:
            file_path = path.Path(file)

            if file_path.is_file():

                if is_corrupted(file_path):
                    self.logger.info(f"Skipping corrupted file: {file_path}")
                    continue
                if "~$" in file_path.stem:
                    self.logger.info(f"Skipping temporary file: {file_path}")
                    continue

                for file_type, extension in self._types.items():
                    file_ext = file_path.suffix
                    if file_ext in set(extension):

                        if is_archive_corrupted(file_path):
                            self.logger.info(f"Skipping corrupted archive: {file_path}")
                            continue
                        if  self._is_protected(file_path):
                            self.logger.info(
                                f"Skipping password-protected archive: {file_path}")
                            continue
                        if is_archive_empty(file_path):
                            self.logger.info(f"Skipping empty archive: {file_path}")
                            continue
                        parsed_files.append(
                            {
                                "File name": file_path.stem,
                                "Extension": file_path.suffix,
                                "Path": file_path,
                                "Type": file_type
                            }
                        )
                        break
        return parsed_files if parsed_files else None

    def _is_protected(self, file_path):
        try:
            if file_path.suffix == ".zip":
                with zipfile.ZipFile(file_path) as zip_ref:
                    # Try to read the first file's content to check for password protection
                    try:
                        zip_ref.read(zip_ref.namelist()[0])
                    except RuntimeError as e:
                        if 'encrypted' in str(e):
                            return True
            elif file_path.suffix == ".7z":
                with py7zr.SevenZipFile(str(file_path), mode='r') as archive:
                    return archive.needs_password()
        except Exception as e:
            self.logger.error(f"Error reading {file_path}: {e}")
        return False

    def _process_file(self, file):
        try:
            file_dest = path.Path(self._dest[file["Type"]])
            if file["Type"] == "Archive" and file["Extension"] in self._types["Archive"]:
                self.logger.info(f"Extracting archive: {file["Path"]}")
                self.archive_handler.extract(file)
            else:
                file_dest = file_dest / dt.datetime.now().strftime("%d-%m-%Y")
                file_dest.mkdir(parents=True, exist_ok=True)
                move_file_with_retry(file, file_dest, delay=3)
                self.logger.info(f"Moved file: {file["Path"]} --> {file_dest}")
        except Exception as e:
            self.logger.error(f"Unexpected error in handle(): {e}")

    def handle(self, files):
        parsed_files = self._parse_file(files)

        if not parsed_files:
            self.logger.info("No files to process.")
            return
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(parsed_files), os.cpu_count()*2)) as executor:
                executor.map(self._process_file, parsed_files)
        except Exception as e:
            self.logger.error(f"Thread pool error: {e}")

        self.logger.info("File handling complete.")


class ArchiveHandler:

    def __init__(self, dest_paths, delete_after_extract=False):
        self._dest = dest_paths
        self._delete_after_extract = delete_after_extract

    def extract(self, file):
        archive_path = file["Path"]
        extract_to = path.Path(self._dest[file["Type"]])/file["File name"]

        try:
            # Ensure extraction directory exists
            extract_to.mkdir(parents=True, exist_ok=True)

            if archive_path.suffix in {".zip", ".tar", ".gz", ".bz2"}:
                shutil.unpack_archive(str(archive_path), str(extract_to))
            elif archive_path.suffix == ".7z":
                with py7zr.SevenZipFile(archive_path, mode="r", password="123") as archive:
                    archive.extractall(extract_to)
            else:
                logging.warning(f"Unsupported archive format: {archive_path.suffix}")
                return

            logging.info(f"Extracted {archive_path.name} to {extract_to}")

            if self._delete_after_extract:
                archive_path.unlink()

        except Exception as e:
            logging.error(f"Failed to extract {archive_path}: {e}")
