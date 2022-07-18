import sqlite3
import threading


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
        with self._lock:
            con = sqlite3.connect("database.db")
            cur = con.cursor()
            cur.execute(
                "INSERT INTO pings VALUES (?, ?, ?)",
                (tracker_id, time, data)
            )
            con.commit()
            con.close()
    
    def fetch_pings(self, tracker_id, count):
        with self._lock:
            con = sqlite3.connect("database.db")
            cur = con.cursor()
            cur.execute(
                "SELECT * FROM pings WHERE tracker_id = ? ORDER BY time DESC LIMIT ?",
                (tracker_id, count)
            )
            pings = cur.fetchall()
            con.close()
            return pings
    
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
        print("Creating database")
        db = Database.getInstance()
        db.create_db()
        print("Done!")
