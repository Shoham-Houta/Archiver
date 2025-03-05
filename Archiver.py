from Utility import FileHandler
import json

with open("config.json") as config_file:
    CONFIG = json.load(config_file)


def main():
    handler = FileHandler(CONFIG["source_path"], CONFIG["dest_paths"],
                          CONFIG["log_path"], CONFIG["log_levels"], CONFIG["file_types"])
    entries = handler.source.iterdir()
    handler.handle(entries)


if __name__ == "__main__":
    main()
