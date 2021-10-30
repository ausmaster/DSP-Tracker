import logging
from time import sleep
from typing import Optional

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from trackerutils import get_now_dsptime
import trackerglobals


def twitch_checkdspstatus(_double_check: bool) -> bool:
    """
    Uses current Selenium browser to determine if DSP is online on Twitch.
    :param _double_check: Internally used to recursively call function again to double check if DSP is online
    :return: True if DSP is online. False is DSP is offline.
    """
    try:
        if _double_check:
            logging.debug("Double Checking Run. Refresh and Wait")
            trackerglobals.BROWSER.get("https://www.duckduckgo.com")
            sleep(2.0)
            trackerglobals.BROWSER.get(trackerglobals.URL)
            sleep(5.0)
            logging.debug("Refreshed. Checking the Second Time.")
        logging.debug("Checking if DSP is online.")
        # Check if the "Follow and get notified when darksydephil is live" text overlay exists.
        _ = WebDriverWait(trackerglobals.BROWSER, 2).until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, 'a[href="/darksydephil"][status="tw-channel-status-indicator--live"')))  # noqa
        if _double_check:
            logging.debug("DSP is online. Returning True.")
            return True
        return twitch_checkdspstatus(True)
    except TimeoutException:
        logging.debug("DSP is offline. Returning False.")
        return False


def twitch_get_videoplayer() -> tuple[Optional[WebElement], Optional[WebElement]]:
    """
    Uses current Selenium browser to setup the webpage to obtain maximum video player webelement dimensions and
    obtains the video player webelement.
    :return: The video player webelement
    """
    # Wait for the Ad to disappear
    try:
        logging.info("Awaiting for Ad completion (if there is any)")
        _ = WebDriverWait(trackerglobals.BROWSER, 90).until_not(
            EC.presence_of_element_located((By.CSS_SELECTOR, "span[data-test-selector=ad-banner-default-text]"))
        )
        logging.info("\tAd Complete. Continuing.")
    except TimeoutException:
        logging.warning("\tAd is longer than expected... continue to screenshot just in case...")

    # Close Side Nav-Bar + Chat-Bar
    try:
        side_nav_bar_collapse: WebElement = WebDriverWait(trackerglobals.BROWSER, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-a-target=side-nav-arrow]")))
        side_nav_bar_collapse.click()
    except TimeoutException:
        logging.warning("Cannot Find Side Nav-Bar collapse. Continuing.")
    try:
        chat_collapse: WebElement = WebDriverWait(trackerglobals.BROWSER, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-a-target=side-nav-arrow]")))
        chat_collapse.click()
    except TimeoutException:
        logging.warning("Cannot Find Chat collapse. Continuing.")

    # Get Stream Time element
    class TwitchTime:
        text = "N/A"

    stream_time = TwitchTime()
    try:
        stream_time = WebDriverWait(trackerglobals.BROWSER, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "live-time"))
        )
    except TimeoutException:
        logging.error("Cannot Find Live Time!")

    # noinspection PyBroadException
    videoplayer_element = None
    # Get Video Player element
    try:
        videoplayer_element = WebDriverWait(trackerglobals.BROWSER, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div[data-a-target=video-player]")))
        logging.info("Video player element gotten.")
    except TimeoutException:
        logging.critical("Could not find video-player element, quitting...")
        trackerglobals.BROWSER.quit()
        exit(1)
    print(f"{get_now_dsptime()}: Tips Tracking setup complete. Starting Tips Tracking.")
    return videoplayer_element, stream_time