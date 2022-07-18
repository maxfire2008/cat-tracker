import serial
import pynmeagps
import datetime
import pytz
import itertools
import time
import struct
import pyotp
import fossil_delta
import hashlib
import zlib
import json
import copy
import requests
import config
from pprint import *

stream = serial.Serial('/dev/serial0', 9600)
nmr = pynmeagps.NMEAReader(stream)

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

def encode_data(DATA):
    ENCODED_DATA = b""
    # secret
    OTP_RN = int(TOTP.now())
    ENCODED_DATA += struct.pack(
        "BBB",
        (OTP_RN >> 16) & 0xff,
        (OTP_RN >> 8) & 0xff,
        OTP_RN & 0xff
    )

    # 'MODE': 3,
    ENCODED_DATA += bytes([DATA.get("MODE", 0)])
    # 'ALTITUDE': 213.4,
    ENCODED_DATA += struct.pack('>e', DATA.get("ALTITUDE", 65519))
    # 'GPS_TIME': datetime.datetime(2022, 7, 10, 4, 18, 9, tzinfo=<UTC>),
    time_short = int(datetime.datetime(2022, 7, 10, 4, 18, 9,
                     tzinfo=pytz.utc).timestamp() % 16777216)

    ENCODED_DATA += struct.pack(
        'BBB',
        (time_short >> 16) & 0xff,
        (time_short >> 8) & 0xff,
        time_short & 0xff,
    )

    # UNPACK with int.from_bytes(struct.unpack('BBB',b'\xcaS\x01'), 'big')

    # 'LATITUDE': ,
    # 'LONGITUDE': ,

    NORTH_LIMIT = config.NORTH_LIMIT
    SOUTH_LIMIT = config.SOUTH_LIMIT
    EAST_LIMIT = config.EAST_LIMIT
    WEST_LIMIT = config.WEST_LIMIT

    lat = struct.pack('>e', transform(
        DATA.get("LATITUDE", 0), NORTH_LIMIT, SOUTH_LIMIT))
    # print(DATA["LATITUDE"])
    # print(lat.hex())
    # print(reverse_transform(struct.unpack('>e', lat)[0], NORTH_LIMIT, SOUTH_LIMIT))

    lon = struct.pack('>e', transform(
        DATA.get("LONGITUDE", 0), EAST_LIMIT, WEST_LIMIT))
    # print(DATA["LONGITUDE"])
    # print(lon.hex())
    # print(reverse_transform(struct.unpack('>e', lon)[0], EAST_LIMIT, WEST_LIMIT))

    ENCODED_DATA += lat
    ENCODED_DATA += lon

    # 'SATELLITES': {1: {'AZIMUTH': 71, 'ELEVATION': 2.0, 'SIGNAL_STRENGTH': ''},
    #             5: {'AZIMUTH': 264, 'ELEVATION': 14.0, 'SIGNAL_STRENGTH': 30},
    #             7: {'AZIMUTH': 85, 'ELEVATION': 49.0, 'SIGNAL_STRENGTH': 25},
    #             8: {'AZIMUTH': 129, 'ELEVATION': 31.0, 'SIGNAL_STRENGTH': 19},
    #             9: {'AZIMUTH': 22, 'ELEVATION': 8.0, 'SIGNAL_STRENGTH': 34},
    #             13: {'AZIMUTH': 230, 'ELEVATION': 37.0, 'SIGNAL_STRENGTH': 22},
    #             14: {'AZIMUTH': 285, 'ELEVATION': 70.0, 'SIGNAL_STRENGTH': 18},
    #             15: {'AZIMUTH': 218, 'ELEVATION': 7.0, 'SIGNAL_STRENGTH': ''},
    #             17: {'AZIMUTH': 0, 'ELEVATION': 20.0, 'SIGNAL_STRENGTH': 36},
    #             19: {'AZIMUTH': 350, 'ELEVATION': 2.0, 'SIGNAL_STRENGTH': 24},
    #             20: {'AZIMUTH': 296, 'ELEVATION': 4.0, 'SIGNAL_STRENGTH': ''},
    #             21: {'AZIMUTH': 91, 'ELEVATION': 9.0, 'SIGNAL_STRENGTH': 15},
    #             27: {'AZIMUTH': 149, 'ELEVATION': 1.0, 'SIGNAL_STRENGTH': ''},
    #             30: {'AZIMUTH': 141, 'ELEVATION': 79.0, 'SIGNAL_STRENGTH': 27},
    #             50: {'AZIMUTH': 331, 'ELEVATION': 36.0, 'SIGNAL_STRENGTH': 31},
    #             193: {'AZIMUTH': '', 'ELEVATION': '', 'SIGNAL_STRENGTH': ''}},

    satellites = []
    for s in DATA["SATELLITES"]:
        csat = ""
        csat += to_bits(s, 8)

        azimuth = DATA["SATELLITES"][s].get("AZIMUTH", 511)
        if type(azimuth) != int:
            azimuth = 511
        csat += to_bits(azimuth, 9)

        elevation = DATA["SATELLITES"][s].get("ELEVATION", 127)
        if type(elevation) == float:
            elevation = int(round(elevation*(2/3)))
        elif type(elevation) == int:
            elevation = int(round(elevation*(2/3)))
        else:
            elevation = 63

        csat += to_bits(elevation, 6)

        csat += to_bits(int(s in DATA["SATELLITES_USED"]), 1)

        # print(s, azimuth, elevation)

        # print(csat)
        # print(len(csat))
        # print(bytes([int(csat[:8],2),int(csat[8:16],2),int(csat[16:],2)]))
        satellites.append(
            bytes([int(csat[:8], 2), int(csat[8:16], 2), int(csat[16:], 2)]))
        # satellites[s]["USED_IN_SOLVE"] = s in DATA["SATELLITES_USED"]

    # print(satellites)
    ENCODED_DATA += bytes([min(255, len(satellites))])
    ENCODED_DATA += b''.join(satellites)

    # 'SPEED': 0.12,
    ENCODED_DATA += struct.pack('>e', DATA.get("SPEED", 65519))
    # 'TRACK': 310.57,
    ENCODED_DATA += struct.pack('>e', DATA.get("TRACK", 65519))
    # 'HORIZONTAL_DILUTION': 0.97,
    ENCODED_DATA += struct.pack('>e', DATA.get("HORIZONTAL_DILUTION", 65519))
    # 'VERTICAL_DILUTION': 0.82
    ENCODED_DATA += struct.pack('>e', DATA.get("VERTICAL_DILUTION", 65519))

    return ENCODED_DATA


DATA = {}

LAST_SEND = time.time()
SEND_INTERVAL = 5
COLLECTED_FROM = {}
LAST_SEND_DATA = None
DELTAS_SENT = 0

REQUESTS = []

SATELLITES_NEW = {}

while True:
    (raw_data, parsed_data) = nmr.read()
    # print(parsed_data.identity)
    if parsed_data.identity == "GPRMC":
        DATA["GPS_TIME"] = datetime.datetime.combine(
            parsed_data.date, parsed_data.time, tzinfo=pytz.utc)
        DATA["LATITUDE"] = noneify(parsed_data.lat)
        DATA["LONGITUDE"] = noneify(parsed_data.lon)
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
    if time.time() > LAST_SEND+SEND_INTERVAL:
        print("Sending data")

        data_to_send = copy.deepcopy(DATA)
        data_to_send["AUTH"] = TOTP.now()
        data_to_send["TRACKER_ID"] = config.TRACKER_ID
        data_to_send["GPS_TIME"] = DATA["GPS_TIME"].timestamp()
        data_to_send["SYSTEM_TIME"] = time.time()

        pprint(data_to_send)
        JSON_DUMP = json.dumps(data_to_send)

        data_encoded = json.dumps(data_to_send).encode()

        if LAST_SEND_DATA and DELTAS_SENT < 100 and config.SEND_DELTAS:
            delta = fossil_delta.create_delta(LAST_SEND_DATA, data_encoded)
            hash = hashlib.md5(data_encoded).digest()[:4]

            print("Hash, delta:", len(hash),len(delta))
            print("Data length:", len(data_encoded))
            print("Data saved:", len(data_encoded)-len(hash)-len(delta))
            data_compressed = zlib.compress(delta,9)
            print("COMPRESSED:", len(data_compressed))

            requests.post(config.SERVER+"/ping",data=b"1"+hash+data_compressed)

            LAST_SEND_DATA = data_encoded
            DELTAS_SENT += 1
        else:
            print("Send original", len(data_encoded))

            hash = hashlib.md5(data_encoded).digest()[:4]
            data_compressed = zlib.compress(data_encoded,9)
            requests.post(config.SERVER+"/ping",data=b"0"+hash+data_compressed)

            LAST_SEND_DATA = data_encoded

        LAST_SEND = time.time()
