import logging
from time import sleep

from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC

from trackerutils import get_now_dsptime
import trackerglobals


def ytp_player_status() -> int:
    return trackerglobals.BROWSER.execute_script("return document.getElementById('movie_player').getPlayerState()")


def ytp_ad_status() -> int:
    return trackerglobals.BROWSER.execute_script("return document.getElementById('movie_player').getAdState()")


def youtube_get_videoplayer():
    videoplayer_element: WebElement

    # Get Video Player element
    try:
        videoplayer_element = WebDriverWait(trackerglobals.BROWSER, 10).until(EC.presence_of_element_located((By.ID, "movie_player")))
        logging.info("Video player element gotten.")
    except TimeoutException:
        logging.critical("Could not find video-player element, quitting...")
        trackerglobals.BROWSER.quit()
        exit(1)
    videoplayer_element.click()  # noqa
    sleep(2.0)
    logging.info("Checking for Ads.")
    # Handle ads, click skip ad if it pops up
    youtube_handle_ads()
    logging.info("Ads complete. Continuing.")
    print(f"{get_now_dsptime()}: Tips Tracking setup complete. Starting Tips Tracking.")
    return videoplayer_element  # noqa


def youtube_handle_ads():
    while ytp_player_status() != 1:
        logging.info("Currently ads, awaiting for Ad completion")
        try:
            skip_button = WebDriverWait(trackerglobals.BROWSER, 20).until(EC.element_to_be_clickable((By.CLASS_NAME, "ytp-ad-skip-button")))
            skip_button.click()
            sleep(2.0)
        except TimeoutException:
            continue


def youtube_checkdspstatus(_ignore) -> bool:
    try:
        logging.debug("Checking if DSP is online.")
        elem = WebDriverWait(trackerglobals.BROWSER, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".style-scope["
                                                                                                "overlay-style=LIVE]")))
        elem.click()
        logging.debug("DSP is online. Returning True.")
        return True
    except TimeoutException:
        logging.debug("DSP is offline. Returning False.")
        return False
