import pathlib as path
import platform
import json
import logging

with open("config.json") as config_file:
    CONFIG = json.load(config_file)

class FileHandler:
    def __init__(self):
        self._platform = CONFIG["platform"]
        self._source = CONFIG["source_path"]
        self._dist = CONFIG["dist_paths"]
        self._logger_output = CONFIG["log_path"]
        self._logger_levels = CONFIG["log_levels"]




class ArchiveExtractor:
    pass