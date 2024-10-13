import logging
import platform
import os
import shutil
import datetime
import time
from py7zr import unpack_7zarchive
from watchdog.events import LoggingEventHandler
from watchdog.observers import Observer

Current_User = "shoha"  # the user that runs the script

# checks the user platform to initialize the correct os path format
if platform.system() == "Windows":
    img_dir: str = rf"C:\Users\{Current_User}\Pictures"
    doc_dir: str = rf"C:\Users\{Current_User}\Documents\Docs"
    pdf_dir: str = rf"C:\Users\{Current_User}\Documents\PDFs"
    presentations_dir: str = rf"C:\Users\{Current_User}\Documents\Presentations"
    logging_dir: str = rf"C:\Users\{Current_User}"
    source: str = rf"C:\Users\{Current_User}\Downloads"
else:
    img_dir: str = ""
    doc_dir: str = ""
    pdf_dir: str = ""
    presentations_dir: str = ""
    source: str = ""


def compressed_entry_handler(entry, dist_path, logger, ext):
    shutil.register_unpack_format('7z', [".7z"], unpack_7zarchive)
    extraction_path = dist_path + rf"\{str(entry.name).removesuffix("." + ext)}"
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
    dir_path = dist_path + fr"\{datetime.datetime.now().strftime("%d-%m-%Y %H-%M")}"
    if not os.path.exists(dir_path):
        os.mkdir(dir_path)
        logger.info(f"{dir_path} - Folder created!")
        shutil.move(entry.path, dir_path)
        logger.info(f"{entry.name} --> {dir_path}")
    else:
        shutil.move(entry.path, dir_path)
        logger.info(f"{entry.name} --> {dir_path}")


def main():
    event_handler: LoggingEventHandler = LoggingEventHandler()
    observer: Observer = Observer()
    observer.schedule(event_handler, source, recursive=True)
    observer.start()
    logger = logging.Logger(name="Archiver", level=logging.INFO)
    file_handler = logging.FileHandler(logging_dir + r"\archiver.log", mode='a', encoding="utf-8")
    formatter = logging.Formatter(
        "{asctime} - {levelname} - {message}",
        style="{",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    try:
        while True:
            time.sleep(1)
            with os.scandir(source) as entries:
                for entry in entries:
                    if ".jpg" in entry.name or ".png" in entry.name:
                        file_entry_handler(entry, img_dir, logger)

                    if ".docx" in entry.name:
                        file_entry_handler(entry, doc_dir, logger)

                    if ".pptx" in entry.name:
                        file_entry_handler(entry, presentations_dir, logger)

                    if ".pdf" in entry.name:
                        file_entry_handler(entry, pdf_dir, logger)

                    if ".zip" in entry.name:
                        compressed_entry_handler(entry, source, logger, 'zip')
                    if ".7z" in entry.name:
                        compressed_entry_handler(entry, source, logger, '7z')

    except KeyboardInterrupt:
        logger.info("Script was stopped!")
        exit(0)


if __name__ == "__main__":
    main()
