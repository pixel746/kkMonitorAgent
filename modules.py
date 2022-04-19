import platform  # For getting the operating system name
import subprocess  # For executing a shell command
import mysql.connector
from pi1wire import Pi1Wire
import logzero
from logzero import logger
from time import sleep
import telepot
import board
import adafruit_dht
import psutil
import requests
import os
import RPi.GPIO as GPIO

logzero.logfile("/home/pi/kkmonitor.log", maxBytes=1e6, backupCount=3)


def update_files():
    main = "https://raw.githubusercontent.com/pixel746/kkMonitorAgent/master/main.py"
    modules = "https://raw.githubusercontent.com/pixel746/kkMonitorAgent/master/modules.py"

    directory = os.getcwd()

    filename = os.path.join(directory, 'main.py')
    r = requests.get(main, auth=('pixel746', 'Oelof@900624'))
    with open(filename, 'w') as f:
        f.write(r.text)

    filename = os.path.join(directory, 'modules.py')
    r = requests.get(modules, auth=('pixel746', 'Oelof@900624'))
    with open(filename, 'w') as f:
        f.write(r.text)


def serial_to_sensor_h(serial):
    sql = f"SELECT name FROM kkHumidityMappings WHERE sensor ='{serial}'"
    _, name = get_sql(sql)

    if _:
        return name[0]['name']


def get_serial():
    # Extract serial from cpuinfo file
    serial = "0000000000000000"
    try:
        f = open('/proc/cpuinfo', 'r')
        for line in f:
            if line[0:6] == 'Serial':
                serial = line[10:26]
        f.close()
        return serial
    except Exception as e:
        print(e)
        logger.error('Could not determine monitor serial.')
        send_msg('Could not determine monitor serial.')
        return False


def send_msg(msg):
    bot = telepot.Bot('1780011684:AAE30i1cW0ia-0gzhk9t_T0IFKXhw3kyZFs')
    bot.sendMessage('-551500159', msg)


def do_sql(query):
    cnx = mysql.connector.connect(user="root", password="help6123", host="192.168.25.149", database="kkDatabase")
    print(query)
    cur = cnx.cursor()
    try:
        cur.execute(query)
        cnx.commit()
        cur.close()
        cnx.close()
        print("Insert Done")
        return True, 'Done'
    except Exception as e:
        cnx.close()
        cur.close()
        print(e)
        return False, e


def get_sql(query):
    cnx = mysql.connector.connect(user="root", password="help6123", host="192.168.25.149", database="kkDatabase")
    cur = cnx.cursor(dictionary=True)
    try:
        cur.execute(query)
        data = cur.fetchall()
        cnx.commit()
        cur.close()
        cnx.close()
        return True, data
    except Exception as e:
        cur.close()
        cnx.close()
        return False, e


def ping(host):
    # Option for the number of packets as a function of
    param = '-n' if platform.system().lower() == 'windows' else '-c'

    # Building the command. Ex: "ping -c 1 google.com"
    command = ['ping', param, '1', host]

    return subprocess.call(command) == 0


def check_sensors():
    serial = get_serial()

    # Try block for getting sensors from mysql database.
    try:
        _, id = get_sql(f"SELECT id FROM kkPIDetails WHERE serial='{serial}'")
        _, pisensors = get_sql(f"SELECT sensor FROM kkSensorMatching WHERE pi_id={id[0]['id']}")
    except Exception as e:
        print(e)
        return False

    # Check serials
    try:
        sens = []
        sensors = Pi1Wire().find_all_sensors()
        if len(sensors) > 0:
            for s in sensors:
                if Pi1Wire().find(s.mac_address).get_temperature() != 0.0:
                    sens.append(s.mac_address)
                else:
                    logger.error(f"Sensor {s.mac_address} has reading of 0. Recovering...")
                    do_reset_reboot()
        else:
            logger.error("No sensors detected. Recovering...")
            do_reset_reboot()
            return False
        print(sens)
    except Exception as e:
        logger.error(str(e))
        return False

    for pisensor in pisensors:
        if pisensor['sensor'] in sens:
            pass
        else:
            logger.error(f"Sensor {pisensor} is not available. Recovering...")
            print(f'sensor {pisensor} is not available.')
            do_reset_reboot()

    return True


def upload_temps(dt):
    try:
        sens = []
        sensors = Pi1Wire().find_all_sensors()
        if len(sensors) > 0:
            for s in sensors:
                if Pi1Wire().find(s.mac_address).get_temperature() > 0.0:
                    sens.append(s.mac_address)
                else:
                    logger.error(f'Sensor {s} has no reading. Recovering...')
                    do_reset_reboot()
                    return False
        else:
            logger.error('No sensors detected. Recovering...')
            do_reset_reboot()
            return False
    except Exception as e:
        logger.error(e)
        return False

    for sensor in sens:
        temp = Pi1Wire().find(sensor).get_temperature()
        if temp == 85.0:
            while temp == 85.0:
                temp = Pi1Wire().find(sensor).get_temperature()

            logger.error(f"Error 85 on probe {sensor}")
            sleep(3)
            c += 1
            upload_temps(dt, c)
        elif temp == 0.0:
            while temp == 0.0:
                temp = Pi1Wire().find(sensor).get_temperature()
            logger.error(f"Error 0 on sensor {sensor}")
            sleep(3)
            c += 1
            upload_temps(dt, c)
        else:
            query = "INSERT INTO kkSensorData (sensor, temp, dt) VALUES ('{}', {}, '{}')".format(sensor, temp, dt)
            query2 = "INSERT INTO kkSensorDataArchive (sensor, temp, dt) VALUES ('{}', {}, '{}')".format(sensor, temp,
                                                                                                         dt)
            try:
                _, x = do_sql(query2)
                _, x = do_sql(query)
            except Exception as e:
                logger.error(e)
                return False
    return True


def upload_humidity(dt):
    for proc in psutil.process_iter():
        if proc.name() == 'libgpiod_pulsein' or proc.name() == 'libgpiod_pulsei':
            proc.kill()

    _, sensors = get_sql(f"SElECT gpio, coldroom FROM kkHumidityMappings WHERE serial='{get_serial()}'")
    if _:
        for sensor in sensors:
            try:
                s = adafruit_dht.DHT22(board.pin.Pin(sensor['gpio']))
                if s.temperature > 0:
                    sens = get_serial() + str(sensor['gpio'])
                    do_sql(f"INSERT INTO kkSensorData (sensor, humidity, dt) VALUES ('{sens}', {s.humidity}, '{dt}')")
                    do_sql(
                        f"INSERT INTO kkSensorDataArchive (sensor, humidity, dt) VALUES ('{sens}', {s.humidity}, '{dt}')")
            except Exception as e:
                logger.error(e)
                send_msg(str(e) + f" on monitor with serial {sensor['coldroom']}")
    else:
        logger.error("Can\'t retrieve humidity sensors from DB.")
        send_msg(
            f"Can\'t retrieve humidity sensors for monitor with serial {get_serial()} from DB.")
    return True


def do_reset_reboot():
    # Power off sensor pins
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(22, GPIO.OUT)
    GPIO.output(22, GPIO.LOW)
    # Wait 5 seconds
    sleep(5)
    # Power on sensor pins
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(22, GPIO.OUT)
    GPIO.output(22, GPIO.HIGH)
    # Reboot monitor
    os.system("sudo reboot")