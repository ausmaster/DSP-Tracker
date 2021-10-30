import logging

import mysql.connector as msql
from mysql.connector import errorcode

import trackerglobals


def setup_mysql(suppress_prints: bool = False) -> None:
    logging.info("Starting MySQL Setup.")
    if not suppress_prints:
        print("Starting MySQL Setup.")
    try:
        trackerglobals.MYSQL_DB = msql.connect(host='localhost', user='tracker', password='dsptr@ck3r', database='dsp_tracker')
    except msql.Error as err:
        if err.errno == errorcode.ER_BAD_DB_ERROR:
            logging.warning("dsp_tracker database does not exist. Creating.")
            trackerglobals.MYSQL_DB = msql.connect(host='localhost', user='tracker', password='dsptr@ck3r')
            cur = trackerglobals.MYSQL_DB.cursor()
            cur.execute("""CREATE database IF NOT EXISTS dsp_tracker""")
            trackerglobals.MYSQL_DB.commit()
            cur.execute("""USE dsp_tracker""")
            # Create the Stream Metadata table
            cur.execute("""CREATE TABLE stream_metadata(
            id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            morning_stream_start TIMESTAMP,
            morning_stream_end TIMESTAMP,
            night_stream_start TIMESTAMP,
            night_stream_end TIMESTAMP,
            tips_goal SMALLINT,
            members_goal SMALLINT)""")
            # Create Tips table
            cur.execute("""CREATE TABLE stream_data(
            id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            local_datetime TIMESTAMP,
            stream_time TIME,
            tips_total DECIMAL(10, 2),
            members_total SMALLINT,
            last_tipper CHAR(50),
            last_tipper_value DECIMAL(10, 2),
            top_tipper CHAR(50),
            top_tipper_value DECIMAL(10, 2))""")
            trackerglobals.MYSQL_DB.commit()
            cur.close()
            trackerglobals.MYSQL_DB = msql.connect(host='localhost', user='tracker', password='dsptr@ck3r', database='dsp_tracker')
            # Set Correct Timezone for Session
            tz = trackerglobals.MORNING_STREAM_TIME.strftime("%z").partition("00")
            trackerglobals.MYSQL_DB.time_zone = tz[0] + ":" + tz[1]
        else:
            logging.critical(f"MySQL ErrNo {err.errno}: {err.msg}")
            exit(1)
    logging.info("MySQL Setup Complete.")
    if not suppress_prints:
        print("MySQL Setup Complete.")