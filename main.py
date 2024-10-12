import logging
import platform
import os
import shutil
import datetime
import time
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


def entry_handler(entry, dist_path, logger):
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
                        entry_handler(entry, img_dir, logger)

                    if ".docx" in entry.name:
                        entry_handler(entry, doc_dir, logger)

                    if ".pptx" in entry.name:
                        entry_handler(entry, presentations_dir, logger)

                    if ".pdf" in entry.name:
                        entry_handler(entry, pdf_dir, logger)

    except KeyboardInterrupt:
        logger.info("Script was stopped!")
        exit(0)


if __name__ == "__main__":
    main()
