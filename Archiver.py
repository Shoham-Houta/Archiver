import logging
import platform
import os
import shutil
import datetime
import time

import smtplib
from email.message import EmailMessage

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

email = EmailMessage()
email["from"] = "shohamho@gmail.com"
email["to"] = "houta@bgu.ac.il"
email["subject"] = "מסמכים להדפסה"


def parse_files(files):
    files_definition = []
    for file in files:
        properties = dict()
        properties["file name"] = file.name
        properties["main type"] = 'application' if ".pdf" in file.name else 'text'
        properties["sub type"] = 'pdf' if ".pdf" in file.name else 'plain'
        properties["path"] = file.path
        properties["entry"] = file
        files_definition.append(properties)
    return files_definition


def create_email_content(files, logger):
    for file in files:
        try:
            with open(file["path"], 'rb') as f:
                file_data = f.read()
            email.add_attachment(file_data, filename=file["file name"], maintype=file["main type"],
                                 subtype=file["sub type"])
            logger.info(f"{file['file name']} added!")
            dest = pdf_dir if ".pdf" in file["file name"] else doc_dir
            file_entry_handler(file["entry"], dest, logger)
        except FileNotFoundError:
            logger.error(f"{file['file name']} Skipped - was not found!")


def send_for_printing(entries, logger: logging.Logger):
    create_email_content(parse_files(entries), logger)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.ehlo()
        smtp.login("shohamho@gmail.com", 'mcpz sdpu cjdm kltq')
        smtp.send_message(email)
    logger.info("Email sent!")


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
    dir_path = dist_path + fr"\{datetime.datetime.now().strftime("%d-%m-%Y")}"
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
                files_to_print = [entry for entry in entries if "להדפסה" in entry.name]
                if files_to_print:
                    send_for_printing(files_to_print, logger)
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
    finally:
        observer.stop()
        observer.join()


if __name__ == "__main__":
    main()
