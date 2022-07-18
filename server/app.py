import flask
import zlib
import fossil_delta
import hashlib
import json
import sqlite3 as database_driver

from pprint import pprint

def get_database():
    return database_driver.connect("database.db")

app = flask.Flask(__name__)

@app.route("/")
def index():
    return "Cat tracker: https://github.com/maxfire2008/cat-tracker"

@app.route("/ping", methods=["POST"])
def ping():
    data = flask.request.get_data()
    if data[0] == 48:
        hash = data[1:5]
        data_encoded = zlib.decompress(data[5:])
        data = json.loads(data_encoded)
        pprint(data)
    # print(data)
    return "", 200