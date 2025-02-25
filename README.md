# Archiver

## Overview

The **Archiver** script is a Python-based automation tool designed to monitor the `Downloads` directory and automatically organize files into categorized folders. It also handles compressed files by extracting them into dedicated directories.

## Features

- Monitors the `Downloads` directory in real-time.
- Automatically moves files to predefined directories based on file type:
  - **Images** (`.jpg`, `.png`) → `Pictures`
  - **Documents** (`.docx`) → `Documents/Docs`
  - **Presentations** (`.pptx`) → `Documents/Presentations`
  - **PDFs** (`.pdf`) → `Documents/PDFs`
- Extracts compressed files (`.zip`, `.7z`) into new folders and removes the archive after extraction.
- Maintains a log file recording file movements and extractions.

## Requirements

- Python 3.x
- Required Python libraries:
  - `watchdog`
  - `py7zr`
  - `logging`
  - `shutil`
  - `datetime`
  - `os`

## Installation

1. Clone or download the script.
2. Install the required dependencies using:
   ```sh
   pip install watchdog py7zr
   ```
   or: 
   ```sh
   pip install -r requirements.txt```

## Usage

Run the script using:

```sh
python Archiver.py
```

The script will begin monitoring the `Downloads` directory and automatically process files as they appear.

## Logging

- A log file (`archiver.log` on Windows, `.archiver.log` on Linux) is created in the user's home directory.
- It records file movements, extractions, and errors.

## Stopping the Script

- The script runs indefinitely; stop it using `Ctrl + C`.

## Platform Compatibility

- **Windows**: Uses `C:\Users\<username>\Downloads`
- **Linux**: Uses `/home/<username>/Downloads`

## Future Enhancements

- Support for additional file types.
- Configurable file paths via a settings file.
- Email notifications for completed actions.

## License

This project is open-source and free to use. Modify and distribute as needed.


