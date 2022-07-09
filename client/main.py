import serial
import pynmeagps
import datetime
import pytz

stream = serial.Serial('/dev/serial0', 9600)
nmr = pynmeagps.NMEAReader(stream)

while True:
    (raw_data, parsed_data) = nmr.read()
    print(parsed_data.identity)
    if parsed_data.identity == "GPRMC":
        print(datetime.datetime.combine(parsed_data.date, parsed_data.time, tzinfo = pytz.utc)-datetime.datetime.now())
    