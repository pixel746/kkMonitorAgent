#!/usr/bin/python3
from modules import *
import time
from datetime import datetime

"""
The following block of code does certain health checks before starting with the temperature and humidity uploads.
"""
update_files()
# Determine identity by serial.
serial = get_serial()

# Check Internet and network.
while True:
    if ping('192.168.1.1'):
        if ping('1.1.1.1'):
            if ping('google.com'):
                break
            else:
                print('DNS resolution not available')
                logger.warning('DNS resolution not available')
        else:
            print('Internet not available.')
            logger.warning('No internet connectivity.')
    else:
        print('No network available.')
        logger.error('No network connectivity.')
    time.sleep(30)

# Check sensors.
if check_sensors():
    pass
else:
    print('Can\'t match sensors from database.')
    logger.error('Cant match sensors from database. Some sensors offline/changes.')
    send_msg(f'Cant match sensors from database. Some sensors offline/changed on monitor with serial {serial}.')

# Send HB
logger.info('All checks passed.')

# Get details
dt = datetime.now()
if upload_temps(dt, 0):
    pass
else:
    logger.error('Could not upload temperatures, please investigate.')
    send_msg(f'Could not upload temperatures, please investigate on monitor with serial {serial}.')
if upload_humidity(dt, 0):
    pass
else:
    logger.error('Could not upload temperatures, please investigate.')
    send_msg(f'Could not upload temperatures, please investigate on monitor with serial {serial}.')
