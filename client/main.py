import serial
import pynmeagps
import datetime
import pytz
import itertools
import time
import pyotp
import fossil_delta
import hashlib
import zlib
import json
import tkinter
import requests
import os
from pprint import *


try:
    print("Press CTRL+C to go to alternate_config.py")
    time.sleep(5)
    print("Using config.py")
    import config
except KeyboardInterrupt:
    print("Using alternate_config.py")
    import alternate_config as config

DATA = {}

LAST_SEND = time.time()
if config.RECORDING:
    SEND_INTERVAL = 5
else:
    SEND_INTERVAL = 1
COLLECTED_FROM = {}
LAST_SEND_DATA = None
DELTAS_SENT = 0

SATELLITES_NEW = {}

DATA_TO_PROCESS = []

if config.RECORDING:
    stream = serial.Serial('/dev/serial0', 9600)
    nmr = pynmeagps.NMEAReader(stream)
else:
    print("PLAYBACK MODE")
    RECORDING_CONTENT = open(input("File:"), "rb").read(
    ).decode().replace("\r\n", "\n").split("\n")

    frame = tkinter.Tk()
    frame.geometry("1500x200")

    def apply(slider_passed=None):
        global DATA
        global COLLECTED_FROM
        global SATELLITES_NEW
        global DATA_TO_PROCESS
        DATA = {}
        COLLECTED_FROM = {}
        SATELLITES_NEW = {}

        if slider_passed:
            slider_value = int(slider_passed)
        else:
            global slider
            slider_value = slider.get()
        print(time.time())
        DATA_TO_PROCESS = RECORDING_CONTENT[max(
            0, int(slider_value)-1000):int(slider_value)]

    slider = tkinter.Scale(frame, from_=0, to=len(
        RECORDING_CONTENT), orient="horizontal", length=1450, command=apply)
    slider.set(0)
    slider.pack()

    reset_button = tkinter.Button(frame, text="Apply", command=apply)
    reset_button.pack()

TOTP = pyotp.TOTP(config.TOTP_SECRET)


def noneify(x):
    if x == '':
        return None
    return x


def transform(number, minimum, maximum):
    return (number-minimum)/(maximum-minimum)


def reverse_transform(number, minimum, maximum):
    return number*(maximum-minimum)+minimum


def to_bits(number, bits, clamp=True):
    if clamp:
        return bin(max(min(number, int('1'*bits, 2)), 0))[2:][-bits:].zfill(bits)
    else:
        return bin(max(number, int('1'*bits, 2), 0))[2:][-bits:].zfill(bits)


while True:
    if config.RECORDING:
        (raw_data, parsed_data) = nmr.read()
        serial_save_path = "/home/pi/serial_data/"+datetime.date.today().strftime("%Y-%m-%d")+"/"+str(datetime.datetime.now().hour)
        os.makedirs(os.path.dirname(serial_save_path), exist_ok=True)
        with open(serial_save_path, "ab+") as file:
            file.write(raw_data)
    else:
        while True:
            raw_data = None
            parsed_data = None
            try:
                raw_data = DATA_TO_PROCESS.pop(0)
            except IndexError:
                pass
            if raw_data:
                try:
                    parsed_data = pynmeagps.NMEAReader.parse(raw_data)
                except pynmeagps.exceptions.NMEAParseError as e:
                    print(e)
            if raw_data and parsed_data:
                break
            frame.update()
    # if len(DATA_TO_PROCESS) % 1000 == 0:
    #     print(len(DATA_TO_PROCESS))
    # print(parsed_data.identity)
    if parsed_data.identity == "GPRMC":
        DATA["GPS_TIME"] = datetime.datetime.combine(
            parsed_data.date, parsed_data.time, tzinfo=pytz.utc).timestamp()
        DATA["LATITUDE"] = noneify(parsed_data.lat)
        DATA["LONGITUDE"] = noneify(parsed_data.lon)

        if parsed_data.lat or "LAST_KNOWN_LATITUDE" not in DATA:
            DATA["LAST_KNOWN_LATITUDE"] = noneify(parsed_data.lat)
            DATA["LAST_KNOWN_LONGITUDE"] = noneify(parsed_data.lon)
            DATA["LAST_KNOWN_LOCATION_TIME"] = datetime.datetime.combine(
                parsed_data.date, parsed_data.time, tzinfo=pytz.utc).timestamp()

        DATA["SPEED"] = noneify(parsed_data.spd)
        DATA["TRACK"] = noneify(parsed_data.cog)

        COLLECTED_FROM["GPRMC"] = True
    if parsed_data.identity == "GPGGA":
        # DATA["SATELLITES"] = parsed_data.numSV
        DATA["ALTITUDE"] = noneify(parsed_data.alt)

        COLLECTED_FROM["GPGGA"] = True
    if parsed_data.identity == "GPGSA":
        # PDOP^2 = HDOP^2 + VDOP^2
        DATA["MODE"] = noneify(parsed_data.navMode)
        DATA["HORIZONTAL_DILUTION"] = noneify(parsed_data.HDOP)
        DATA["VERTICAL_DILUTION"] = noneify(parsed_data.VDOP)
        DATA["SATELLITES_USED"] = []
        for i in range(1, 13):
            exec("current_prn = parsed_data.svid_"+str(i).zfill(2))
            if current_prn:
                DATA["SATELLITES_USED"].append(current_prn)

        COLLECTED_FROM["GPGSA"] = True
    if parsed_data.identity == "GPGSV":
        if parsed_data.msgNum == 1:
            SATELLITES_NEW = {}
        for i in itertools.count(start=1):
            try:
                exec("svid = parsed_data.svid_"+str(i).zfill(2))
                exec("elevation = parsed_data.elv_"+str(i).zfill(2))
                exec("azimuth = parsed_data.az_"+str(i).zfill(2))
                exec("signal_strength = parsed_data.cno_"+str(i).zfill(2))
                SATELLITES_NEW[int(svid)] = {
                    "ELEVATION": noneify(elevation),
                    "AZIMUTH": noneify(azimuth),
                    "SIGNAL_STRENGTH": noneify(signal_strength)
                }
            except AttributeError as e:
                # print(e)
                break
        if parsed_data.numMsg == parsed_data.msgNum:
            DATA["SATELLITES"] = SATELLITES_NEW

        COLLECTED_FROM["GPGSV"] = True
    if (time.time() > LAST_SEND+SEND_INTERVAL and config.RECORDING) or ((not config.RECORDING) and len(DATA_TO_PROCESS) == 0):
        print("Sending data")

        data_to_send = {}
        data_to_send["AUTH"] = TOTP.now()
        data_to_send["TRACKER_ID"] = config.TRACKER_ID
        data_to_send["GPS_TIME"] = DATA.get("GPS_TIME", None)
        data_to_send["SYSTEM_TIME"] = time.time()
        data_to_send["DATA"] = DATA

        # pprint(data_to_send)
        JSON_DUMP = json.dumps(data_to_send)

        data_encoded = json.dumps(data_to_send).encode()

        if LAST_SEND_DATA and DELTAS_SENT < 100 and config.SEND_DELTAS:
            delta = fossil_delta.create_delta(LAST_SEND_DATA, data_encoded)
            hash = hashlib.md5(data_encoded).digest()[:4]
            last_send_data_hash = hashlib.md5(LAST_SEND_DATA).digest()[:4]

            print("Hash, delta:", len(hash), len(delta))
            print("Data length:", len(data_encoded))
            print("Data saved:", len(data_encoded)-len(hash)-len(delta))
            data_compressed = zlib.compress(delta, 9)
            print("COMPRESSED:", len(data_compressed))

            try:
                resp = requests.post(
                    config.SERVER+"/ping", data=b"1"+last_send_data_hash+hash+data_compressed)
                print(resp)
            except Exception as e:
                print(e)

            LAST_SEND_DATA = data_encoded
            DELTAS_SENT += 1
        else:
            print("Send original", len(data_encoded))

            hash = hashlib.md5(data_encoded).digest()[:4]
            data_compressed = zlib.compress(data_encoded, 9)

            print("compressed version", len(data_compressed))

            try:
                resp = requests.post(config.SERVER+"/ping",
                                     data=b"0"+hash+data_compressed)
                print(resp)
            except Exception as e:
                print(e)

            LAST_SEND_DATA = data_encoded

        LAST_SEND = time.time()
    if not config.RECORDING:
        frame.update()
