import datetime
import logging
import os


import hikari

from airy import ROOT_DIR
from airy.config import db_config


async def backup_database() -> hikari.File:
    """Attempts to back up the database via pg_dump into the db_backup directory"""
    logging.info("Performing daily database backup...")

    username: str = db_config.user
    password: str = db_config.password
    hostname: str = db_config.host
    port: str = db_config.port
    db_name: str = db_config.db

    os.environ["PGPASSWORD"] = password

    if not os.path.isdir(os.path.join(ROOT_DIR, "backup")):
        os.mkdir(os.path.join(ROOT_DIR, "backup"))

    now = datetime.datetime.now(datetime.timezone.utc)

    filename: str = f"{now.year}-{now.month}-{now.day}_{now.hour}_{now.minute}_{now.second}.pgdmp"
    backup_path: str = os.path.join(ROOT_DIR, "backup", filename)

    return_code = os.system(
        f"pg_basebackup -x -h db01.example.com -U backup -D /backup"
    )
    os.environ["PGPASSWORD"] = ""

    if return_code != 0:
        raise RuntimeError("pg_dump failed to create a database backup file!")

    logging.info("Database backup complete!")
    return hikari.File(backup_path)
