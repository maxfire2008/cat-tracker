import sqlite3
import threading
import json


class Database:
    _instance = None
    _lock = threading.Lock()

    @staticmethod
    def getInstance():
        """ Static access method. """
        if Database._instance == None:
            Database()
        return Database._instance

    def __init__(self):
        """ Virtually private constructor. """
        if Database._instance != None:
            raise Exception("The class 'Database' is a singleton!")
        else:
            Database._instance = self

    def write_ping(self, tracker_id, time, data):
        print(tracker_id, time, data)
        with self._lock:
            con = sqlite3.connect("database.db")
            cur = con.cursor()
            cur.execute(
                "INSERT INTO pings VALUES (?, ?, ?)",
                (tracker_id, time, json.dumps(data))
            )
            con.commit()
            con.close()

    def fetch_pings(self, tracker_id=None, limit=None, clean=True):
        with self._lock:
            con = sqlite3.connect("database.db")
            cur = con.cursor()
            cur.execute(
                "SELECT * FROM pings " +
                ("WHERE tracker_id = ?" if tracker_id !=
                 None else "") +
                "ORDER BY time DESC " +
                ("LIMIT ?" if limit != None else ""),
                tuple(
                    filter(
                        lambda x: x != None,
                        [tracker_id, limit]
                    )
                )
            )
            pings = cur.fetchall()
            con.close()

            return [
                {
                    "tracker_id": p[0],
                    "time": p[1],
                    "data": json.loads(p[2])["DATA"]
                }
                for p in pings
            ]

    def create_db(self):
        with self._lock:
            con = sqlite3.connect("database.db")
            cur = con.cursor()
            cur.execute(
                '''CREATE TABLE pings
                (tracker_id text, time integer, data text)'''
            )
            con.commit()
            con.close()


if __name__ == "__main__":
    if input("Would you like to create the database? (y/N)") == "y":
        input("Please delete database.db then press ENTER")
        print("Creating database")
        db = Database.getInstance()
        db.create_db()
        print("Done!")
