import sqlite3
import config



def new_connection():
    cnx = sqlite3.connect(config.database, isolation_level="DEFERRED")
    cur = cnx.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA threads=4")
    return cnx



def create_tables(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_report (
            date TEXT,
            country TEXT,
            state TEXT,
            admin2 TEXT,
            confirmed INT,
            deaths INT,
            recovered INT,
            PRIMARY KEY (date, country, state, admin2)
        )
    """)
