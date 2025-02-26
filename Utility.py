import pathlib as path
import datetime as dt
import logging
import shutil
import time
import tracemalloc
import functools
import sys
import platform


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
        print(f"    Memory Usage: {current / 1024:.2f} KB (Peak: {peak / 1024:.2f} KB)")

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
            print(f"Attempt #{attempt+1}:\nFile {file['File name']} is locked (likely by antivirus). Retrying in {delay} seconds...")
        time.sleep(delay)  # Wait before retrying
    print(f"Skipping {file['File name']}: Still locked after {retries} attempts.")


class FileHandler:
    def __init__(self,source,dist_paths,logger_output,logger_lvls,types):
        self._source = path.Path(source)
        self._dist:dict = dist_paths
        self._logger_output = path.Path(logger_output)
        self._logger_levels:list = logger_lvls
        self._types:dict = types

    @property
    def source(self):
        return self._source

    
    def _parse_file(self,files):
        parsed_files = []
        for file in files:
            file_path = path.Path(file)

            if file_path.is_file():
                file_ext = file_path.suffix

                for file_type, extension in self._types.items():
                    if file_ext in extension:
                        parsed_files.append(
                            {
                                "File name":file_path.stem,
                                "Extension": file_path.suffix,
                                "Path" : file_path,
                                "Type": file_type
                            }
                        )
                        break
        return parsed_files if parsed_files else None

    def handle(self, files):
        parsed_files = self._parse_file(files)
        try:
            for file in parsed_files:
                file_dest = path.Path(self._dist[file["Type"]])
                file_dest = file_dest / dt.datetime.now().strftime("%d-%m-%Y")
                file_dest.mkdir(parents=True,exist_ok=True)
                move_file_with_retry(file,file_dest,delay=3)
        except TypeError:
            print("No files.")
        except Exception as e:
            print(f"Unexpected error in handle(): {e}")




class ArchiveExtractor:
    pass

if __name__=="__main__":
    import json
    # the user that runs the script
    if platform.system() == "Windows":
        import msvcrt  # Windows file locking
    else:
        import fcntl  # Linux/macOS file locking

    with open("config.json") as config_file:
        CONFIG = json.load(config_file)

    handler = FileHandler(CONFIG["source_path"],CONFIG["dist_paths"],CONFIG["log_path"],CONFIG["log_levels"],CONFIG["file_types"])
    entries = handler.source.iterdir()
    handler.handle(entries)