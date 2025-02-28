import pathlib as path
import datetime as dt
import logging
import shutil
import time
import tracemalloc
import functools
import platform
import py7zr
import zipfile


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
                print(f"{file['File name']} ---> {destination}")
                return  # Success
            except PermissionError:
                print(f"Permission denied: {file['Path']}. Retrying...")
            except FileNotFoundError:
                print(f"Error: {file['Path']} not found. Skipping...")
                return
            except Exception as e:
                print(f"Unexpected error: {e}. Skipping {file['Path']}...")
                return
        else:
            print(
                f"Attempt #{attempt+1}:\nFile {file['File name']} is locked (likely by antivirus). Retrying in {delay} seconds...")
        time.sleep(delay)  # Wait before retrying
    print(
        f"Skipping {file['File name']}: Still locked after {retries} attempts.")


class FileHandler:
    def __init__(self, source, dest_paths, logger_output, logger_lvls, types, delete_archives=False):
        self._source = path.Path(source)
        self._dest: dict = dest_paths
        self._logger_output = path.Path(logger_output)
        self._logger_levels: list = logger_lvls
        self._types: dict = types
        self.archive_handler = ArchiveHandler(
            dest_paths, delete_after_extract=delete_archives)

    @property
    def source(self):
        return self._source

    def _parse_file(self, files):
        parsed_files = []
        for file in files:
            file_path = path.Path(file)

            if file_path.is_file():
                file_ext = file_path.suffix

                if file_ext in self._types["Archive"] and self._is_protected(file_path):
                    print(f"Skipping password-protected archive: {file_path}")
                    continue

                for file_type, extension in self._types.items():
                    if file_ext in extension and "~$" not in file_path.stem:
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
            print(f"Error reading {file_path}: {e}")
        return False

    def handle(self, files):
        parsed_files = self._parse_file(files)
        try:
            for file in parsed_files:
                if file["Type"] == "Archive" and file["Extension"] in self._types["Archive"]:
                    self.archive_handler.extract(file)
                else:
                    file_dest = path.Path(self._dest[file["Type"]])
                    file_dest = file_dest / dt.datetime.now().strftime("%d-%m-%Y")
                    file_dest.mkdir(parents=True, exist_ok=True)
                    move_file_with_retry(file, file_dest, delay=3)
        except TypeError:
            print("No files.")
        except Exception as e:
            print(f"Unexpected error in handle(): {e}")


class ArchiveHandler():

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
                print(f"Unsupported archive format: {archive_path.suffix}")
                return

            print(f"Extracted {archive_path.name} to {extract_to}")

            if self._delete_after_extract:
                archive_path.unlink()

        except Exception as e:
            print(f"Failed to extract {archive_path}: {e}")


if __name__ == "__main__":
    import json
    # the user that runs the script
    if platform.system() == "Windows":
        import msvcrt  # Windows file locking
    else:
        import fcntl  # Linux/macOS file locking

    with open("config.json") as config_file:
        CONFIG = json.load(config_file)

    handler = FileHandler(CONFIG["source_path"], CONFIG["dest_paths"],
                          CONFIG["log_path"], CONFIG["log_levels"], CONFIG["file_types"], True)
    entries = handler.source.iterdir()
    handler.handle(entries)
