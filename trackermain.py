# Import Standard Libraries
import argparse
import logging
from datetime import datetime
import os
from json import dumps
from time import sleep
from typing import Optional

# Other Tracker Files
import trackerglobals as tg
import trackerutils
import trackeryoutube
import trackertwitch
import trackermysql

# Selenium Imports
from selenium.common.exceptions import StaleElementReferenceException, WebDriverException
from selenium.webdriver import Chrome
from selenium.webdriver.remote.webelement import WebElement

# Pytesseract and Pillow Imports
from PIL import Image
import pytesseract

# MySQL connector imports
import mysql.connector as msql

# Pytz Imports
from pytz import timezone

# Alive-Progress Imports
from alive_progress import alive_bar

pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"


def parse_args() -> tuple[int, str]:
    """
    Parses command line arguments
    :return: Tuple of number for log level and mode selected
    """
    parse = argparse.ArgumentParser()
    parse.add_argument(
        "-log",
        "--log",
        default="warning",
        help=(
            "Provide logging level. "
            "Example --log DEBUG', default='WARNING'"),
    )
    parse.add_argument(
        "-mode",
        "--mode",
        default="youtube",
        help=("Specifies whether it monitors YouTube or Twitch. Accepted values: youtube, twitch . "
              "Example --mode youtube. default='youtube'")
    )
    arg_options = parse.parse_args()
    num_level = getattr(logging, arg_options.log.upper())
    mode = arg_options.mode.lower()
    if not isinstance(num_level, int):
        raise ValueError('Invalid log level: %s' % arg_options.log)
    if mode not in ["youtube", "twitch"]:
        raise ValueError(f"Invalid mode: {arg_options.mode}")
    if mode == "youtube":
        tg.URL = "https://www.youtube.com/user/DSPGaming"
    else:
        tg.URL = "https://www.twitch.tv/darksydephil"
    return num_level, mode


def setup_logger(level: int) -> None:
    """
    Setup the logger to log events. Do once before anything else.
    :return: None
    """
    print("Starting Logger Setup.")
    # noinspection PyArgumentList
    logging.basicConfig(filename="trackerlog.log", encoding="iso-8859-1",
                        format="[%(asctime)s] - %(levelname)s: %(message)s [END]", level=level)
    logging.info("Logger Setup Complete.")
    print("Logger Setup Complete.")


def setup_browser(suppress_prints: bool = False, url: str = "") -> None:
    """
    Spawns a new Selenium browser to control, global var BROWSER is the Selenium browser
    :return: None
    """
    logging.info("Browser Setup Starting...")
    if not suppress_prints:
        print("Starting Browser Setup.")
    try:
        tg.BROWSER = Chrome(executable_path=os.path.abspath("chromedriver"), options=tg.OPTIONS)
    except WebDriverException as e:
        logging.error(str(e).strip())
        logging.error("Retrying, max 2 times.")
        for i in range(1, 2):
            try:
                logging.warning(f"Try #{i}")
                sleep(10.0)
                tg.BROWSER = Chrome(executable_path=os.path.abspath("chromedriver"), options=tg.OPTIONS)
                logging.warning("Success! Continuing back to main function.")
                break
            except Exception as e:
                logging.error(str(e).strip())
                logging.warning(f"Trying {2 - i} more times.")
                continue
        else:
            logging.error("Too many tries to restart. Cutting off and exiting.")
            print("Could not start Browser. Quitting Tracker.")
            tg.SQLITE_DB.close()
            exit(1)
    logging.info(f"Browser Created. Going to Darksydephil "
                 f"{'YouTube' if tg.URL == 'https://www.youtube.com/user/DSPGaming' else 'Twitch'}.")
    # Ensure Browser is at proper resolution
    window_size = tg.BROWSER.get_window_size()
    if window_size["width"] < 1920 and window_size["height"] < 1080:
        logging.warning(f"Window Size less than 1920x1080 -> Current: {window_size['width']}x{window_size['height']}")
        logging.warning(f"Resizing Window.")
        tg.BROWSER.set_window_size(1920, 1080)
        # Check to ensure
        window_size = tg.BROWSER.get_window_size()
        if window_size["width"] != 1920 and window_size["height"] != 1080:
            logging.critical(f"Resolution not at 1920x1080! -> {window_size['width']}x{window_size['height']}")
            raise Exception("Window Sizing not successful. Required Resolution = 1920x1080")
    if url:
        tg.BROWSER.get(url)
    else:
        tg.BROWSER.get(tg.URL)

    # Wait 5 second for page to come up
    sleep(5.0)
    # Alert User of Completion
    logging.info("Browser Setup Complete.")
    if not suppress_prints:
        print("Browser Setup Complete.")


def get_dsp_screenshot(video_player: WebElement) -> int:
    """
    Takes a screenshot of the stream and saves it to the imagecache
    :param video_player: The video player WebElement that has DSP's stream
    :return: The screenshot number that was saved
    """
    # Using Video Player element, screenshot and increment counter
    curr_screenshot_num = tg.SS_COUNTER
    video_player.screenshot(os.path.abspath(f"imagecache/screenshot{curr_screenshot_num}.png"))
    logging.debug(f"Saved screenshot {curr_screenshot_num} to screenshot{curr_screenshot_num}.png")
    if tg.SS_COUNTER == 3:
        tg.SS_COUNTER = 0
    else:
        tg.SS_COUNTER += 1
    return curr_screenshot_num


def tesseract_processing(screenshot_num: int, t_mode: bool, stream_time: WebElement = None) -> Optional[dict]:
    """
    Takes the selected screenshot from the screenshot image cache, crops it, and runs the OCR on it.
    :param screenshot_num: The screenshot number in the imagecache folder
    :param t_mode: Specifies "twitch" mode. True if DSP is streaming on Twitch, False if DSP is streaming on YouTube.
    :param stream_time: WebElement for Twitch stream time if using Twitch mode
    :return: Dictionary of the OCR data, None if it cannot interpret at least one piece of information from it
    """
    with Image.open(f"imagecache/screenshot{screenshot_num}.png") as im:
        if t_mode:
            img_top = im.crop((100, 0, 1200, 32))
            img_bottom = im.crop((240, 700, 1140, 754))
        else:
            img_top = im.crop((0, 0, 1280, 32))
            img_bottom = im.crop((0, 693, 1280, 720))
        img_top.save(os.path.abspath(f"imagecache/screenshot{screenshot_num}_topcrop.png"))
        logging.debug(f"Saved cropped screenshot{screenshot_num}_topcrop.png")
        img_bottom.save(os.path.abspath(f"imagecache/screenshot{screenshot_num}_bottomcrop.png"))
        logging.debug(f"Saved cropped screenshot{screenshot_num}_bottomcrop.png")
        tipsstr_top = pytesseract.image_to_string(img_top, config=r"--dpi 300 --psm 7")
        tipsstr_bottom = pytesseract.image_to_string(img_bottom, config=r"--dpi 300 --psm 7")
        utc_time = datetime.now(timezone("Etc/GMT-0")).isoformat(timespec="seconds")
        local_time = datetime.now(timezone("America/Los_Angeles")).isoformat(timespec="seconds")
        stream_time_str = stream_time.text if stream_time else None
        logging.debug(f"Current Tips String {stream_time_str} -\nTop:\n{tipsstr_top}\nBottom:\n{tipsstr_bottom}\n")
        tips_dict = {"utc_time": utc_time, "local_time": local_time, "stream_time": stream_time_str,
                     "members_total": None, "last_tip": None, "top_tip": None, "tips_met": None, "tips_total": None}
        get_lasttip = True
        get_toptip = True
        get_tipgoal = True
        get_members = True
        info_str = "Items Skipped: "
        # Last Tip Regex Get
        try:
            last_tip = tg.LAST_TIP_REGEX.findall(tipsstr_top)[0]
            tips_dict["last_tip"] = last_tip
            logging.debug(f"Top Text found. Last Tip set to {last_tip}")
        except IndexError:
            try:
                last_tip = tg.LAST_TIP_REGEX.findall(tipsstr_bottom)[0]
                tips_dict["last_tip"] = last_tip
                logging.debug(f"Bottom Text found. Last Tip set to {last_tip}")
            except IndexError:
                info_str += "last_tip "
                get_lasttip = False
        # Top Tip Regex get
        try:
            top_tip = tg.TOP_TIP_REGEX.findall(tipsstr_top)[0]
            tips_dict["top_tip"] = top_tip
            logging.debug(f"Top Text found. Top Tip set to {top_tip}")
        except IndexError:
            try:
                top_tip = tg.TOP_TIP_REGEX.findall(tipsstr_bottom)[0]
                tips_dict["top_tip"] = top_tip
                logging.debug(f"Bottom Text found. Top Tip set to {top_tip}")
            except IndexError:
                info_str += "top_tip "
                get_toptip = False
        # Tips Goal Regex get
        try:
            tips_goal = tg.TIPS_GOAL_REGEX.findall(tipsstr_top)[0]
            if not tips_goal[0]:
                tips_dict['tips_met'] = True
                tips_dict["tips_total"] = tips_goal[1]
                logging.debug(f"Top Text found. Tips Met set to True, Tips Goal set to {tips_goal[1]}")
            else:
                tips_dict["tips_met"] = False
                tips_dict["tips_total"] = tips_goal[0]
                logging.debug(f"Top Text found. Tips Met set to False, Tips Goal set to {tips_goal[0]}")
        except IndexError:
            try:
                tips_goal = tg.TIPS_GOAL_REGEX.findall(tipsstr_bottom)[0]
                if not tips_goal[0]:
                    tips_dict['tips_met'] = True
                    tips_dict["tips_total"] = tips_goal[1]
                    logging.debug(f"Bottom Text found. Tips Met set to True, Tips Goal set to {tips_goal[1]}")
                else:
                    tips_dict["tips_met"] = False
                    tips_dict["tips_total"] = tips_goal[0]
                    logging.debug(f"Bottom Text found. Tips Met set to False, Tips Goal set to {tips_goal[0]}")
            except IndexError:
                info_str += "tips_goal "
                get_tipgoal = False
        # Members Goal Regex get
        try:
            members_goal = tg.MEMBERS_REGEX.findall(tipsstr_top)[0]
            if not members_goal[0]:
                tips_dict["members_total"] = members_goal[1]
                logging.debug(f"Top Text found. Members Goal set to {members_goal[1]}")
            else:
                tips_dict["members_total"] = members_goal[0]
                logging.debug(f"Top Text found. Members Goal set to {members_goal[0]}")
        except IndexError:
            try:
                members_goal = tg.MEMBERS_REGEX.findall(tipsstr_bottom)[0]
                if not members_goal[0]:
                    tips_dict["members_total"] = members_goal[1]
                    logging.debug(f"Bottom Text found. Members Goal set to {members_goal[1]}")
                else:
                    tips_dict["members_total"] = members_goal[0]
                    logging.debug(f"Bottom Text found. Members Goal set to {members_goal[0]}")
            except IndexError:
                info_str += "members_goal"
                get_members = False
        # Log if get no info
        if not get_toptip or not get_toptip or not get_tipgoal or not get_members:
            logging.info(info_str)
        # If we get all errors, no point returning anything, just return None
        if not (get_lasttip or get_toptip or get_tipgoal or get_members):
            return None
        logging.debug(f"Returning -> {tips_dict}")
        return tips_dict


def process_data(data: dict) -> tuple:
    """
    Process returned data from tesseract_processing() to a SQLite insertable form
    :param data: Returned data dictionary from tesseract_processing()
    :return: SQL insertable tuple, each entry of type [str or None, float or None]
    """
    # Process Last Tip
    last_tipper = None
    last_tip_val = None
    if data["last_tip"]:
        last_tipper = tg.PROC_LASTORTOP_TIP.findall(data["last_tip"])
        if last_tipper:
            last_tipper, last_tip_val = last_tipper[0]
            last_tip_val = float(last_tip_val)
        else:
            last_tipper = None

    # Process Top Tip
    top_tipper = None
    top_tip_val = None
    if data["top_tip"]:
        top_tipper = tg.PROC_LASTORTOP_TIP.findall(data["top_tip"])
        if top_tipper:
            top_tipper, top_tip_val = top_tipper[0]
            top_tip_val = float(top_tip_val)
        else:
            top_tipper = None

    # Process Tips Goal
    tips_total = None
    tips_goal = None
    if data["tips_total"]:
        tips_total = tg.PROC_TIPS_GOAL.findall(data["tips_total"])
        if tips_total:
            if len(tips_total) == 2:
                tips_goal = float(tips_total[1].strip("$"))
            tips_total = float(tips_total[0].strip("$"))
        else:
            tips_total = None

    # Process Members Total
    members = None
    members_goal = None
    if data["members_total"]:
        members = tg.PROC_MEMBERS.findall(data["members_total"])
        if members:
            if len(members) == 2:
                members_goal = int(members[1])
            members = int(members[0])
        else:
            members = None
    return data["local_time"], data["stream_time"], tips_total, members, last_tipper, last_tip_val, \
           top_tipper, top_tip_val, tips_goal, members_goal


def start_information_gathering(prog_bar: alive_bar, t_mode: bool) -> None:
    """
    Main function to start the Tips Tracking. Will run indefinitely until DSP's stream is offline, then returns.
    :param prog_bar: The progress bar associated with the DSP tracker
    :param t_mode: Specifies "twitch" mode. True if DSP is streaming on Twitch, False if DSP is streaming on YouTube.
    :return: None
    """

    def mysql_tracking_loop(cursor: msql.connection):
        def mysql_end_time_insert():
            nonlocal cursor, curr_metadata
            if not curr_metadata:
                return
            if tg.CLOSEST_STREAM == 1:
                cursor.execute("""UPDATE stream_metadata SET morning_stream_end = NOW() WHERE id = %s""",
                               (curr_metadata[0],))
                logging.debug("SQL Inserted current time into morning_stream_end")
            else:
                cursor.execute("""UPDATE stream_metadata SET night_stream_end = NOW() WHERE id = %s""",
                               (curr_metadata[0],))
                logging.debug("SQL Inserted current time into night_stream_end")
            tg.MYSQL_DB.commit()

        def close_tracking():
            print(f"{trackerutils.get_now_dsptime()}: Tips tracking finished. Darksydephil is now offline. Returning "
                  f"back to DSP Online/Offline Monitoring.")
            logging.warning(
                "Tips tracking finished. Darksydephil is now offline. Returning back to DSP Online/Offline "
                "Monitoring.")
            mysql_end_time_insert()
            tg.BROWSER.get(tg.URL)

        cursor.execute(
            """SELECT * 
            FROM stream_metadata 
            WHERE (morning_stream_start LIKE CONCAT(CURRENT_DATE(), "%")) OR (night_stream_start LIKE CONCAT(CURRENT_DATE(), "%"))"""
        )
        curr_metadata = cursor.fetchall()
        logging.debug(f"Current Initial Metadata fetch: {curr_metadata}")
        logging.debug(f"Current Closest Stream: {tg.CLOSEST_STREAM}")
        if not curr_metadata:
            # If nothing, insert a row
            if tg.CLOSEST_STREAM == 1:
                logging.debug(
                    "No initial row for today has been inserted for metadata. Inserting data for morning stream.")
                cursor.execute(
                    """INSERT INTO stream_metadata (morning_stream_start) VALUES (NOW())""")
                tg.MYSQL_DB.commit()
            else:
                logging.debug(
                    "No initial row for today has been inserted for metadata. Inserting data for night stream.")
                cursor.execute(
                    """INSERT INTO stream_metadata (night_stream_start) VALUES (NOW())""")
                tg.MYSQL_DB.commit()
            cursor.execute(
                """SELECT * 
                FROM stream_metadata 
                WHERE (morning_stream_start LIKE CONCAT(CURRENT_DATE(), "%")) OR (night_stream_start LIKE CONCAT(CURRENT_DATE(), "%"))"""
            )
            curr_metadata = list(cursor.fetchall()[0])
        else:
            # If something, ensure correct information is there
            curr_metadata = list(curr_metadata[0])
            # If morning stream, ensure stream start is set to now
            if tg.CLOSEST_STREAM == 1:
                if not curr_metadata[1]:
                    logging.debug("Closest stream is morning, updating morning_stream_start to now.")
                    cursor.execute("""UPDATE stream_metadata SET morning_stream_start = NOW() WHERE id = %s""",
                                   (curr_metadata[0],))
                    tg.MYSQL_DB.commit()
                    curr_metadata[1] = "CURRENT"
            # If night stream, ensure stream start is set to now
            else:
                if not curr_metadata[5]:
                    logging.debug("Closest stream is night, updating night_stream_start to now.")
                    cursor.execute("""UPDATE stream_metadata SET night_stream_start = NOW() WHERE id = %s""",
                                   (curr_metadata[0],))
                    tg.MYSQL_DB.commit()
                    curr_metadata[5] = "CURRENT"
        logging.debug(f"Final resulting metadata fetch: {curr_metadata}")
        try:
            last_data = (None, None, None, None, None, None, None, None)
            while True:
                # Before processing, make sure no ads are there
                if trackeryoutube.ytp_ad_status() == 1:
                    trackeryoutube.youtube_handle_ads()
                # Get Screenshot
                screen_num = get_dsp_screenshot(vid_player)
                # Crop Screenshot, run through OCR, find usable tips data, return tips data
                return_data = tesseract_processing(screen_num, t_mode, stream_t_elem)
                # If no usable data, don't commit to database
                if return_data:
                    # Process data first
                    *tips_data, tips_goal, members_total = process_data(return_data)
                    # Keep out the $0 at the start of the stream
                    if tips_data[2] == float(0):
                        # Delay 5 seconds then process another
                        sleep(5.0)
                        continue
                    if tg.CLOSEST_STREAM == 1 and not curr_metadata[3]:
                        cursor.execute(
                            f"""UPDATE stream_metadata SET morning_stream_tipgoal = %s WHERE id = %s""",
                            (tips_goal, curr_metadata[0]))
                        tg.MYSQL_DB.commit()
                        curr_metadata[3] = tips_goal
                    elif tg.CLOSEST_STREAM == 2 and not curr_metadata[7]:
                        cursor.execute(
                            f"""UPDATE stream_metadata SET night_stream_tipgoal = %s WHERE id = %s""",
                            (tips_goal, curr_metadata[0]))
                        tg.MYSQL_DB.commit()
                        curr_metadata[7] = tips_goal
                    if tg.CLOSEST_STREAM == 1 and not curr_metadata[4]:
                        cursor.execute(
                            f"""UPDATE stream_metadata SET morning_stream_membergoal = %s WHERE id = %s""",
                            (members_total, curr_metadata[0]))
                        tg.MYSQL_DB.commit()
                        curr_metadata[4] = members_total
                    elif tg.CLOSEST_STREAM == 2 and not curr_metadata[8]:
                        cursor.execute(
                            f"""UPDATE stream_metadata SET night_stream_membergoal = %s WHERE id = %s""",
                            (members_total, curr_metadata[0]))
                        tg.MYSQL_DB.commit()
                        curr_metadata[8] = members_total
                    if (tips_data[2] != last_data[2] and tips_data[2]) \
                            or (tips_data[3] != last_data[3] and tips_data[3]) \
                            or (tips_data[4] != last_data[4] and tips_data[4]) \
                            or (tips_data[5] != last_data[5] and tips_data[5]) \
                            or (tips_data[6] != last_data[6] and tips_data[6]) \
                            or (tips_data[7] != last_data[7] and tips_data[7]):
                        try:
                            cursor.execute("""INSERT INTO stream_data (local_datetime, stream_time, tips_total, 
                            members_total, last_tipper, last_tipper_value, top_tipper, top_tipper_value) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""", tuple(tips_data))
                            last_data = tips_data
                            tg.MYSQL_DB.commit()
                            prog_bar()
                        except msql.errors.DataError as d:
                            logging.warning(f"SQL DataError has occurred. {d}. Skipping Insert.")
                            continue
                # Delay 5 seconds then process another
                sleep(5.0)
                # If on YouTube mode, check if current URL has changed. If changed, DSP has gone offline
                # (Means video has changed).
                if not t_mode:
                    temp_track_var = trackeryoutube.ytp_player_status()
                    if (curr_url != tg.BROWSER.current_url) or (temp_track_var == 0):
                        logging.info(f"Closing Tracking with Player Status {temp_track_var}")
                        close_tracking()
                        sleep(10.0)
                        return
        except KeyboardInterrupt:
            print("Keyboard Interrupted. Quitting.")
            close_tracking()
            tg.MYSQL_DB.close()
            exit(0)

    def sqlite_tracking_loop():
        cursor = tg.SQLITE_DB.cursor()
        while True:
            # Get Screenshot
            screen_num = get_dsp_screenshot(vid_player)
            # Crop Screenshot, run through OCR, find usable tips data, return tips data
            return_data = tesseract_processing(screen_num, t_mode, stream_t_elem)
            # If no usable data, don't commit to database
            if return_data:
                # Process data first
                utc_time, local_time, stream_time, last_t, last_t_val, top_t, top_t_val, t_total, t_goal = \
                    process_data(return_data)
                sql_query = """INSERT INTO tips_data (local_datetime, utc_datetime, stream_time, tips_total, last_tipper, last_tipper_value, top_tipper, top_tipper_value) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""  # noqa
                cursor.execute(sql_query, (local_time, utc_time, stream_time, t_total, last_t, last_t_val, top_t,
                                           top_t_val))
                tg.SQLITE_DB.commit()
                prog_bar()
            # Delay 5 seconds then process another
            sleep(5.0)
            # If on YouTube mode, check if current URL has changed. If changed, DSP has gone offline
            # (Means video has changed).
            if not t_mode:
                if curr_url != tg.BROWSER.current_url:
                    print(f"{trackerutils.get_now_dsptime()}: Tips tracking finished. Darksydephil is now offline. Returning "
                          f"back to DSP Online/Offline Monitoring.")
                    logging.warning(
                        "Tips tracking finished. Darksydephil is now offline. Returning back to DSP Online/Offline "
                        "Monitoring.")
                    tg.BROWSER.get(tg.URL)
                    sleep(10.0)
                    return

    def outputfile_tracking_loop():
        # Ensure output folder exists
        if not os.path.exists(os.path.abspath("output")):
            logging.warning("output folder does not exist. Creating.")
            os.mkdir(os.path.abspath("output"))
            logging.warning("Created.")
        # Ensure output folder for day exists
        if not os.path.exists(os.path.abspath(f"output/{current_date}")):
            logging.warning(f"output/{current_date} folder does not exist. Creating.")
            os.mkdir(os.path.abspath(f"output/{current_date}"))
            logging.warning("Created.")
        with open(os.path.abspath(f"output/{current_date}/output{current_date}T{current_time}.txt"),
                  "w") as log_output_file:  # noqa
            while True:
                # Get Screenshot
                screen_num = get_dsp_screenshot(vid_player)
                # Crop Screenshot, run through OCR, find usable tips data, return tips data
                return_data = tesseract_processing(screen_num, t_mode, stream_t_elem)
                # If no usable data, don't write to file
                if return_data:
                    return_data = dumps(return_data)
                    log_output_file.write(return_data + "\n")
                    prog_bar()
                # Delay 5 seconds then process another
                sleep(5.0)

    # Ensure screenshots cache folder exists
    if not os.path.exists(os.path.abspath("imagecache")):
        logging.warning("imagecache folder does not exist. Creating.")
        os.mkdir(os.path.abspath("imagecache"))
        logging.warning("Created.")
    full_local_datetime = datetime.now(timezone("America/Los_Angeles")).isoformat(timespec="seconds")
    current_date, current_time = full_local_datetime.split("T")
    current_time = current_time.split("-")[0]
    # Get the Video Player
    stream_t_elem = None
    if t_mode:
        vid_player, stream_t_elem = trackertwitch.twitch_get_videoplayer()
    else:
        vid_player = trackeryoutube.youtube_get_videoplayer()
    # Main Event Loops
    try:
        logging.info("Starting Information Gathering main loop.")
        curr_url = tg.BROWSER.current_url
        if tg.MYSQL_DB:
            try:
                sql_cur = tg.MYSQL_DB.cursor()
            except msql.errors.OperationalError as m:
                logging.warning(f"MySQL Operational Error {m} has occurred. Trying to get cursor max 2 times.")
                for i in range(2):
                    try:
                        tg.MYSQL_DB.close()
                        sleep(5.0)
                        tg.MYSQL_DB = msql.connect(host='localhost', user='tracker', password='dsptr@ck3r', database='dsp_tracker')
                        sql_cur = tg.MYSQL_DB.cursor()
                        break
                    except Exception as e:
                        logging.warning(f"Exception occured on time {i}: {e}. Continuing.")
                        continue
                else:
                    logging.critical("Could not get MySQL Cursor. Quitting.")
                    tg.MYSQL_DB.close()
                    exit(1)
            mysql_tracking_loop(sql_cur)
        elif tg.SQLITE_DB:
            sqlite_tracking_loop()
        else:
            outputfile_tracking_loop()
    except KeyboardInterrupt:
        print(f"{trackerutils.get_now_dsptime()}: Tips tracking finished. Keyboard Interrupted. Quitting.")
        logging.error("Keyboard Interrupt. Exiting.")
        tg.BROWSER.quit()
        if tg.SQLITE_DB:
            tg.SQLITE_DB.close()
        if tg.MYSQL_DB:
            tg.MYSQL_DB.close()
        exit(0)
    except StaleElementReferenceException:
        # For Twitch, will automatically boot off the livestream to channel and will throw this error, means to go
        print(f"{trackerutils.get_now_dsptime()}: Tips tracking finished. Darksydephil is now offline. Returning back to DSP "
              f"Online/Offline Monitoring.")
        logging.warning("Tips tracking finished. Darksydephil is now offline. Returning back to DSP Online/Offline "
                        "Monitoring.")
        sleep(30.0)
        tg.BROWSER.refresh()
        sleep(10.0)
        tg.BROWSER.refresh()
        sleep(10.0)
        return


if __name__ == '__main__':
    # Print Intro Banner
    print(tg.INTRO_BANNER)
    # Print Setup Phase
    print(tg.BORDER)
    print("\t   SETUP PHASE")
    print(tg.BORDER)
    # Parse Command Line Arguments
    num_level, mode = parse_args()
    check_func = trackertwitch.twitch_checkdspstatus if mode == "twitch" else trackeryoutube.youtube_checkdspstatus
    # Setup the Logger
    setup_logger(num_level)
    # Setup the Database
    trackermysql.setup_mysql()
    # Setup the Browser
    setup_browser()
    print(tg.BORDER)
    # DSP Online/Offline Monitoring: Check every 120 secs if Offline status, else DSP online -> Begin Tips Tracking
    try:
        logging.info("Starting DSP Online/Offline monitoring process.")
        print("Starting DSP Tracking.")
        with alive_bar(unknown='dots_waves', spinner='pulse', calibrate=20, enrich_print=False) as bar:
            bar.text("Online/Offline Monitoring DSP...")
            while True:
                # Wait for DSP to be online, if online -> gather info
                if check_func(False):
                    logging.info("DSP is online now. Starting Information Gathering.")
                    # Refresh page to make ensure it sees the main DSP Twitch stream page
                    # noinspection PyUnboundLocalVariable
                    tg.BROWSER.refresh()
                    sleep(5.0)
                    logging.info("DSP is online. Starting Tips Tracking.")
                    bar.text("Tips Tracking DSP...")
                    # Run DSP information gathering
                    if mode == "twitch":
                        start_information_gathering(bar, True)
                    else:
                        start_information_gathering(bar, False)
                    bar.text("Online/Offline Monitoring DSP...")
                else:
                    stream_timedelta: float
                    tg.CLOSEST_STREAM = trackerutils.determine_closest_stream()
                    if tg.CLOSEST_STREAM == 1:
                        tg.MORNING_STREAM_TIME = datetime.now(timezone("America/Los_Angeles")).replace(hour=10,
                                                                                                    minute=45,
                                                                                                    second=0,
                                                                                                    microsecond=0)
                        stream_timedelta = abs((tg.MORNING_STREAM_TIME
                                                - datetime.now(timezone("America/Los_Angeles"))).total_seconds())
                    else:
                        tg.NIGHT_STREAM_TIME = datetime.now(timezone("America/Los_Angeles")).replace(hour=18,
                                                                                                  minute=45,
                                                                                                  second=0,
                                                                                                  microsecond=0)
                        stream_timedelta = abs((tg.NIGHT_STREAM_TIME
                                                - datetime.now(timezone("America/Los_Angeles"))).total_seconds())
                    logging.debug(f"Current Stream Delta: {stream_timedelta} with closest stream: {'Day' if tg.CLOSEST_STREAM == 1 else 'Night'}")
                    # If closest stream is more than an hour away, hibernation mode
                    if stream_timedelta > 3600.0:
                        logging.info("DSP is currently offline and currently more than an hour from closest stream.")
                        # Quit the current browser
                        tg.BROWSER.quit()
                        # Sleep for an hour
                        logging.info("Stopped browser and sleeping for an hour.")
                        sleep(3600.0)
                        # Recalculate stream times in case there is a new day
                        tg.MORNING_STREAM_TIME = datetime.now(timezone("America/Los_Angeles")).replace(hour=10,
                                                                                                    minute=45,
                                                                                                    second=0,
                                                                                                    microsecond=0)
                        tg.NIGHT_STREAM_TIME = datetime.now(timezone("America/Los_Angeles")).replace(hour=18,
                                                                                                  minute=45,
                                                                                                  second=0,
                                                                                                  microsecond=0)
                        logging.debug("Refreshed Stream Times.")
                        logging.debug(f"Current Morning Stream Time: {tg.MORNING_STREAM_TIME}")
                        logging.debug(f"Current Night Stream Time: {tg.NIGHT_STREAM_TIME}")
                        logging.debug(f"Closest Stream is {'Morning Stream' if tg.CLOSEST_STREAM == 1 else 'Night Stream'}"
                                      f" and it is {int(stream_timedelta)} seconds away.")
                        # Wake up, make another browser
                        setup_browser(suppress_prints=True)
                        # Ensure browser is ready to go
                        sleep(10.0)
                    # Else its an hour before stream time, check every 2 minutes
                    else:
                        logging.info("DSP currently offline. Refreshing and waiting 2 minutes.")
                        # Refresh page and ensure the Offline banner does not exist before checking again
                        # noinspection PyUnboundLocalVariable
                        tg.BROWSER.refresh()
                        sleep(120.0)
    except KeyboardInterrupt:
        print("Keyboard Interrupted. Quitting.")
        logging.error("Keyboard Interrupted. Quitting.")
        tg.BROWSER.quit()
        if tg.SQLITE_DB:
            tg.SQLITE_DB.close()
        if tg.MYSQL_DB:
            tg.MYSQL_DB.close()
        exit(0)
    # except Exception as e:
    #     logging.critical(str(e).strip())
    #     logging.critical("Quitting!")
    #     BROWSER.quit()
    #     SQL_CONNECTION.close()
    #     exit(1)
