import re
import sqlite3
from datetime import datetime
from typing import Union

import mysql.connector as msql
from pytz import timezone
from selenium.webdriver import Chrome
from selenium.webdriver import ChromeOptions

from trackerutils import determine_closest_stream

INTRO_BANNER = '''                                                                                                                                 
######                                                         
#     # ###### ##### #####    ##    ####  #    # ###### #####  
#     # #        #   #    #  #  #  #    # #   #  #      #    # 
#     # #####    #   #    # #    # #      ####   #####  #    # 
#     # #        #   #####  ###### #      #  #   #      #####  
#     # #        #   #   #  #    # #    # #   #  #      #   #  
######  ######   #   #    # #    #  ####  #    # ###### #    # 

#     #                                            #                  
##   ##   ##   #####  ######    #####  #   #      # #   #    #  ####  
# # # #  #  #  #    # #         #    #  # #      #   #  #    # #      
#  #  # #    # #    # #####     #####    #      #     # #    #  ####  
#     # ###### #    # #         #    #   #      ####### #    #      # 
#     # #    # #    # #         #    #   #      #     # #    # #    # 
#     # #    # #####  ######    #####    #      #     #  ####   ####                                                                                                                                     
'''
BORDER = "⋆﹥━━━━━━━━━━━━━━━━━━━━━━━━━━━━﹤⋆"
'''
All inclusive Regex -> Last\sTip:\s(.*)\sTop\sTip:\s(.*)\sTips\sGoal:\s(.*)

TIPS_REGEX = re.compile(r"Subs:\s(\d+)\s(?:Ton|Top)\s*Cheer:\s(.*)\s(?:Ton|Top)\s(?:Tin|Tip):\s(.*)\s(?:Tins|Tips)\sGoal:\s(.*)")
'''
# Regex Globals
LAST_TIP_REGEX = re.compile(r"Last\s*Super.*:\s(.*\)).*To.\s*T")
TOP_TIP_REGEX = re.compile(r"To.\s*Ti.:\s(.*\)).*[a-zA-Z]")
TIPS_GOAL_REGEX = re.compile(r"(?:Goal:|Total:)\s*(?:(\$\d+/\$\d+)|(\$\d+))")
MEMBERS_REGEX = re.compile(r"(?:Members:)\s*(?:(\d+/\d+)|(\d+))")
PROC_LASTORTOP_TIP = re.compile(r"(.*?)\s*(?:[^a-zA-Z0-9]*)\$(\d+\.*\d*)")
PROC_TIPS_GOAL = re.compile(r"\$?\d+\.*\d*")
PROC_MEMBERS = re.compile(r"\d+")

# Selenium Globals
BROWSER: Chrome
OPTIONS = ChromeOptions()
OPTIONS.headless = True
OPTIONS.binary_location = "/usr/bin/google-chrome"
OPTIONS.add_argument("window-size=1920x1080")
OPTIONS.add_argument("--no-sandbox")
OPTIONS.add_argument("--disable-default-apps")
OPTIONS.add_argument("--enable-precise-memory-info")
OPTIONS.add_experimental_option("excludeSwitches", ["enable-logging"])
URL: str
SS_COUNTER = 0

# Datetime Globals
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
UTC_DATETIME_FORMAT = " (%H:%M:%S UTC)"
MORNING_STREAM_TIME = datetime.now(timezone("America/Los_Angeles")).replace(hour=10, minute=45, second=0, microsecond=0)
NIGHT_STREAM_TIME = datetime.now(timezone("America/Los_Angeles")).replace(hour=18, minute=45, second=0, microsecond=0)

# 1 = Morning Stream, 2 = Night Stream
CLOSEST_STREAM: int = determine_closest_stream()

# DB Globals
# noinspection PyTypeChecker
SQLITE_DB: sqlite3.Connection = None
# noinspection PyTypeChecker
MYSQL_DB: Union[msql.MySQLConnection, msql.CMySQLConnection] = None

# Test Variables
TEST_DSP_ONLINE = True