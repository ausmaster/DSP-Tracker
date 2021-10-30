import logging
from datetime import datetime
from json import dumps
from time import sleep
from urllib import request

from pytz import timezone
from selenium.common.exceptions import StaleElementReferenceException

import trackerglobals


def determine_closest_stream() -> int:
    if abs((trackerglobals.MORNING_STREAM_TIME - datetime.now(timezone("America/Los_Angeles"))).total_seconds()) \
            < abs((trackerglobals.NIGHT_STREAM_TIME - datetime.now(timezone("America/Los_Angeles"))).total_seconds()):
        return 1
    else:
        return 2


def get_now_dsptime() -> str:
    return str(datetime.now(timezone("America/Los_Angeles")).strftime(trackerglobals.DATETIME_FORMAT)) + str(datetime.now(timezone(
        "Etc/GMT-0")).strftime(trackerglobals.UTC_DATETIME_FORMAT))


def test_selenium_exception() -> None:
    try:
        while True:
            if not trackerglobals.TEST_DSP_ONLINE:
                break
            raise StaleElementReferenceException("Test Exception")
    except StaleElementReferenceException:
        print("Tracking Finished.")
        logging.warning("Darksydephil is now offline.")
        sleep(2.0)
        trackerglobals.BROWSER.refresh()
        return


def test_dsp_online() -> None:
    trackerglobals.TEST_DSP_ONLINE = not trackerglobals.TEST_DSP_ONLINE
    return


def send_post_data(data: dict) -> None:
    post_req = request.Request("http://127.0.0.1:8000", headers={"Content-Type": "application/json; charset=utf-8"})
    json_data = dumps(data).encode("utf-8")
    # noinspection PyTypeChecker
    post_req.add_header("Content-Length", len(json_data))
    request.urlopen(post_req, json_data)