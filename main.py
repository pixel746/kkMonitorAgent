#!/usr/bin/python3
from modules import *
import time
from datetime import datetime

"""
The following block of code does certain health checks before starting with the temperature and humidity uploads.
try:
    update_files()
except Exception as e:
    logger.error(str(e))
"""


# Determine identity by serial.
serial = get_serial()

# Check Internet and network.
while True:
    if ping('192.168.25.149'):
        break
    else:
        print('No network available.')
        logger.error('No network connectivity.')
    time.sleep(300)

# Check sensors.
if check_sensors():
    pass
else:
    print('Can\'t match sensors from database. Recovering...')
    logger.error('Cant match sensors from database. Some sensors offline/changes. Recovering...')
    send_msg(f'Cant match sensors from database. Some sensors offline/changed on monitor with serial {serial}. Recovering...')
    do_reset_reboot()

# Send HB
logger.info('All checks passed.')

# Get details
dt = datetime.now()
if upload_temps(dt):
    pass
else:
    logger.error('Could not upload temperatures, please investigate.')
    send_msg(f'Could not upload temperatures, please investigate on monitor with serial {serial}.')
if upload_humidity(dt):
    pass
else:
    logger.error('Could not upload temperatures, please investigate.')
    send_msg(f'Could not upload temperatures, please investigate on monitor with serial {serial}.')
