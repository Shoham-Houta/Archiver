import pathlib as path
import datetime as dt
import logging
import shutil
import time
import tracemalloc
import functools


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
    
    @performance_debug
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
        for file in parsed_files:
            file_dist = path.Path(self._dist[file["Type"]])
            if file_dist.exists():
                try:
                    file_dist = file_dist / dt.datetime.now().strftime("%d-%m-%Y")
                    file_dist.mkdir()
                    self._distribute_file(file,file_dist)
                except FileExistsError:
                        print("Path exists.")
                        self._distribute_file(file,file_dist)
                except PermissionError:
                    print(f"Permission denied: Cannot move the file {file["Path"]} to {file_dist}")
                except Exception as e:
                    print(f"Error moving file: {e}")

    @staticmethod
    def _distribute_file(file, dist):
            print(f"{file["File name"]} --> {dist}")
            shutil.move(file["Path"], dist)
class ArchiveExtractor:
    pass

if __name__=="__main__":
    import json
    # the user that runs the script
    with open("config.json") as config_file:
        CONFIG = json.load(config_file)

    handler = FileHandler(CONFIG["source_path"],CONFIG["dist_paths"],CONFIG["log_path"],CONFIG["log_levels"],CONFIG["file_types"])
    entries= handler.source.iterdir()
    handler.handle(entries)