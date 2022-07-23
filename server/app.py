import flask
import zlib
import fossil_delta
import hashlib
import json
import flask_socketio
import config
import time
import sqlite3_database_driver as database_driver

from pprint import pprint

app = flask.Flask(__name__)
socketio = flask_socketio.SocketIO(app)


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
            tracker_id = data["TRACKER_ID"]
            db.write_ping(tracker_id,
                          time.time(), data)
            try:
                latest_ping = db.fetch_pings(tracker_id=tracker_id, limit=1)[0]
                flask_socketio.send(
                    message=latest_ping,
                    to=tracker_id,
                    namespace="/"
                )
            except IndexError:
                pass
            # pprint(data)
        else:
            print("Data was malformed")
            return "", 400
    if request_data[0] == 49:
        return "", 501
    # print(data)
    return "", 200


@app.route("/fetch_pings")
def fetch_pings():
    db = database_driver.Database.getInstance()
    pings = db.fetch_pings(
        tracker_id=flask.request.args.get("tracker_id", ""),
        limit=flask.request.args.get("limit", 100)
    )
    # return "<br>".join([", ".join([str(y) for y in x]) for x in pings])
    return json.dumps(pings, indent=4)


@app.route("/view/<tracker_id>")
def view(tracker_id):
    return flask.render_template("view.html", tracker_id=tracker_id, MAPBOX_TOKEN=config.MAPBOX_TOKEN)


@socketio.on('join')
def on_join(data):
    tracker_id = data["tracker_id"]
    flask_socketio.join_room(tracker_id)
    # flask_socketio.send('New viewer of tracker', to=tracker_id)

    db = database_driver.Database.getInstance()
    try:
        latest_ping = db.fetch_pings(tracker_id=tracker_id, limit=1)[0]
        flask_socketio.send(
            message=latest_ping,
            to=tracker_id,
            namespace="/"
        )
    except IndexError:
        pass


@socketio.on('leave')
def on_leave(data):
    tracker_id = data["tracker_id"]
    flask_socketio.leave_room(tracker_id)
    # flask_socketio.send('Lost viewer of tracker', to=tracker_id)


if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", use_reloader=True, debug=True, )
