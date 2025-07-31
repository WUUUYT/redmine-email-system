import os
import sys
import msal
import logging
import logging.config
from pathlib import Path
from loguru import logger
from email_reader import EmailReader
from redmine_handler import RedmineHandler
from monitor_sender import MonitorSender
from msal import PublicClientApplication
from config.settings import *


def clear_attachments_folder(
    folder_path=Path(__file__).resolve().parent / "attachments",
):
    if os.path.exists(folder_path):
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")


# CACHE_FILE = Path(__file__).resolve().parent / "data/token_cache.bin"


def load_cache(CACHE_FILE):
    cache = msal.SerializableTokenCache()
    if os.path.exists(Path(__file__).resolve().parent / CACHE_FILE):
        cache.deserialize(
            open(Path(__file__).resolve().parent / CACHE_FILE, "r").read()
        )
    return cache


def save_cache(cache, CACHE_FILE):
    if cache.has_state_changed:
        with open(Path(__file__).resolve().parent / CACHE_FILE, "w") as f:
            f.write(cache.serialize())


def get_access_token(CACHE_FILE, email_address):
    cache = load_cache(CACHE_FILE)
    logging.config.dictConfig(LOGGING_CONFIG)
    logger = logging.getLogger("main")
    app = PublicClientApplication(
        APP_CONFIG["client_ID"],
        authority=f"https://login.microsoftonline.com/{APP_CONFIG['tenant_ID']}",
        token_cache=cache,
    )
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(["Mail.Read"], account=accounts[0])
        if result:
            logger.info("Old access token obtained!")
            save_cache(cache, CACHE_FILE)
            return result["access_token"]
    # First time manual login.
    flow = app.initiate_device_flow(scopes=["Mail.Read"])
    logger.info(f"Please login using {email_address}")
    logger.info(flow["message"])
    result = app.acquire_token_by_device_flow(flow)
    if "access_token" in result:
        logger.info("New access token obtained!")
        save_cache(cache, CACHE_FILE)
        return result["access_token"]
    logger.info("No access token obtained.")
    return None


def main(project_id, project_info):
    logging.config.dictConfig(LOGGING_CONFIG)
    access_token = get_access_token(project_info["cache_file"], project_info["email"])

    monitorsender = MonitorSender(project_id=project_id, access_token=access_token)
    monitorsender.find_updated_issue_within()
    monitorsender.process_emails()

    emailreader = EmailReader(access_token=access_token)
    emailreader.logger = logging.getLogger("email_reader")
    emailreader.connect_read()
    emailreader.reading_emails()

    if emailreader.emails_data:
        redminehandler = RedmineHandler(
            project_id=project_id,
            emails_data=emailreader.emails_data,
            access_token=access_token,
        )
        redminehandler.login()
        redminehandler.redmine_write()


if __name__ == "__main__":
    try:
        for project_id, project_info in APP_CONFIG["projects"].items():
            if project_info["enabled"]:
                main(project_id, project_info)
                clear_attachments_folder()

    except Exception as e:
        logger.exception(f"Error occurred in main execution: {e}")
        sys.exit(1)
