import flask
import zlib
import fossil_delta
import hashlib
import json
import sqlite3_database_driver as database_driver

from pprint import pprint

app = flask.Flask(__name__)

@app.route("/")
def index():
    return "Cat tracker: https://github.com/maxfire2008/cat-tracker"

@app.route("/ping", methods=["POST"])
def ping():
    request_data = flask.request.get_data()
    if request_data[0] == 48:
        hash = request_data[1:5]
        data_encoded = zlib.decompress(request_data[5:])
        if hashlib.md5(data_encoded).digest()[:4] == hash:
            data = json.loads(data_encoded)
            db = database_driver.Database.getInstance()
            db.write_ping(data["TRACKER_ID"], data["GPS_TIME"], data_encoded)
            pprint(data)
        else:
            print("Data was malformed")
            return "", 400
    if request_data[0] == 49:
        return "", 501
    # print(data)
    return "", 200

@app.route("/fetch_pings")
def fetch_pings():
    