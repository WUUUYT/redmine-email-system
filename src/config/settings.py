import os
import json
from pathlib import Path

# Base Directory
BASE_DIR = Path(__file__).parent.parent

log_dir = Path(__file__).resolve().parent.parent.parent / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "%(asctime)s [%(name)s] %(levelname)s: %(message)s"}
    },
    "handlers": {
        "monitor_sender": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": str(log_dir / "monitor_sender.log"),
            "when": "midnight",
            "backupCount": 7,
            "formatter": "simple",
            "encoding": "utf-8",  
        },
        "email_reader": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": str(log_dir / "email_reader.log"),
            "when": "midnight",
            "backupCount": 7,
            "formatter": "simple",
            "encoding": "utf-8",
        },
        "redmine_handler": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": str(log_dir / "redmine_handler.log"),
            "when": "midnight",
            "backupCount": 7,
            "formatter": "simple",
            "encoding": "utf-8",
        },
        "main_handler": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": str(log_dir / "main.log"),
            "when": "midnight",
            "backupCount": 7,
            "formatter": "simple",
            "encoding": "utf-8",
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "monitor_sender": {
            "handlers": ["monitor_sender", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "email_reader": {
            "handlers": ["email_reader", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "redmine_handler": {
            "handlers": ["redmine_handler", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "main": {
            "handlers": ["main_handler", "console"],
            "level": "INFO",
            "propagate": False,
        },
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
}
# email configurations
EMAIL_CONFIG = {
    "mailbox": os.getenv("MAILBOX_FOLDER"),
    "processed_files": "data/processed_time.txt",
}
# Redmine
REDMINE_CONFIG = {
    "url": os.getenv("REDMINE_URL"),
    "apikey": os.getenv("REDMINE_APIKEY"),
    "project_id": "",
    "processed_files": "data/processed_issue.txt",
}


def load_config(config_path):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config


config_path = "./config.json"

APP_CONFIG = load_config(config_path)
