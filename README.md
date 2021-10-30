# Detracker (aka. DSP Tracker)
Detracker is a Python application designed to track the user reported tips of infamous content creator: DarkSydePhil.

## High Level Overview
- Creates controlled web-browser
- Checks to see if DSP is online per interval
- Starts tracking once online
- Takes screenshot of video window of the bar where his "tip information" is
- Uses OCR to read the information
- Store information in database
- Stop tracking when offline
- Goes back to checking if DSP is online per interval

## Disclaimer
This applciation uses already existing public information (DSP streams and uploads videos on a public platform).
I am not promoting the harassment of DSP with this application. 
I am not responsible for any user who utilizes information collected via this application.