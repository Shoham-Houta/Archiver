import logging
import platform
import os
import shutil
import datetime
import time

from py7zr import unpack_7zarchive
from watchdog.events import LoggingEventHandler
from watchdog.observers import Observer

from Utility import FileHandler
import json
# the user that runs the script
Current_User = os.popen("whoami").read().strip()
with open("config.json") as config_file:
    CONFIG = json.load(config_file)

handler = FileHandler(CONFIG["source_path"],CONFIG["dist_paths"],CONFIG["log_path"],CONFIG["log_levels"],CONFIG["file_types"])


def compressed_entry_handler(entry, dist_path, logger, ext):
    shutil.register_unpack_format('7z', [".7z"], unpack_7zarchive)
    extraction_path = dist_path + \
        rf"\{str(entry.name).removesuffix("." + ext)}"
    if not os.path.exists(extraction_path):
        os.mkdir(extraction_path)
        logger.info(f"{extraction_path} - Folder created!")
        shutil.unpack_archive(entry.path, extraction_path, ext)
        logger.info(f"{entry.name} extracted to {extraction_path}")
        os.remove(entry.path)
        logger.info(f"{entry.name} was deleted!")
    else:
        shutil.unpack_archive(entry.path, extraction_path, ext)
        logger.info(f"{entry.name} extracted to {extraction_path}")
        os.remove(entry.path)
        logger.info(f"{entry.name} was deleted!")


def file_entry_handler(entry, dist_path, logger):
    dir_path = dist_path + fr"\{datetime.datetime.now().strftime("%d-%m-%Y")}" if platform.system() == "Windows" else dist_path + f"/{datetime.datetime.now().strftime("%d-%m-%Y")}"
    if not os.path.exists(dir_path):
        os.mkdir(dir_path)
        logger.info(f"{dir_path} - Folder created!")
        shutil.move(entry.path, dir_path)
        logger.info(f"{entry.name} --> {dir_path}")
    else:
        shutil.move(entry.path, dir_path)
        logger.info(f"{entry.name} --> {dir_path}")


def main():
    # event_handler: LoggingEventHandler = LoggingEventHandler()
    # observer = Observer()
    # observer.schedule(event_handler, source, recursive=True)
    # observer.start()
    # logger = logging.Logger(name="Archiver", level=logging.INFO)
    # file_handler = logging.FileHandler(logging_dir + "archiver.log", mode='a', encoding="utf-8") if platform.system(
    # ) == "Windows" else logging.FileHandler(logging_dir + ".archiver.log", mode='a', encoding="utf-8")
    # formatter = logging.Formatter(
    #     "{asctime} - {levelname} - {message}",
    #     style="{",
    #     datefmt="%Y-%m-%d %H:%M:%S"
    # )

    # file_handler.setFormatter(formatter)
    # logger.addHandler(file_handler)

    try:
        while True:
            # time.sleep(1)
            with os.scandir(handler.source) as entries:
                for entry in entries:
                    handler.Handle(entry)
    except KeyboardInterrupt:
        exit(0)


if __name__ == "__main__":
    main()
