import logging
import os
import sqlite3

import trackerglobals


def setup_sqlite_database() -> None:
    # Ensure database folder exists
    if not os.path.exists(os.path.abspath("db")):
        logging.warning("db folder does not exist. Creating.")
        os.mkdir(os.path.abspath("db"))
        logging.warning("Created.")
    trackerglobals.SQLITE_DB = sqlite3.connect(os.path.abspath("db/dsptrackerdatabase.db"))
    cursor = trackerglobals.SQLITE_DB.cursor()
    cursor.execute("""SELECT count(name) FROM sqlite_master WHERE type='table' AND name='tips_data'""")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""CREATE TABLE tips_data (id integer primary key, local_datetime text, 
        utc_datetime text, stream_time text, tips_total double, last_tipper text, last_tipper_value double, 
        top_tipper text, top_tipper_value double)""")
    cursor.execute("""SELECT count(name) FROM sqlite_master WHERE type='table' AND name='stream_metadata'""")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""CREATE TABLE stream_metadata (id integer primary key, daystream_start text, 
        daystream_end text, nightstream_start, nightstream_end text, tips_goal double)""")