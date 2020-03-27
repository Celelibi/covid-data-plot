#!/usr/bin/env python3

import sys
import glob
import datetime
import sqlite3
import csv

import db


def remapfields(entry):
    mapfields = {
        "Last Update": "date",
        "Last_Update": "date",
        "Country/Region": "country",
        "Country_Region": "country",
        "Province/State": "state",
        "Province_State": "state",
        "Admin2": "admin2",
        "Confirmed": "confirmed",
        "Deaths": "deaths",
        "Recovered": "recovered"
    }
    for k, v in list(entry.items()):
        if k not in mapfields:
            continue
        entry[mapfields[k]] = entry[k]
        del entry[k]

    return entry



def parse_date(date):
    try:
        return datetime.datetime.fromisoformat(date)
    except ValueError:
        pass

    try:
        return datetime.datetime.strptime(date, "%m/%d/%y %H:%M")
    except ValueError:
        pass

    try:
        return datetime.datetime.strptime(date, "%m/%d/%Y %H:%M")
    except ValueError:
        pass

    raise ValueError("parse_date: No format for date: " + date)



def intornone(v):
    if v is None or isinstance(v, int):
        return v
    if v == "":
        return None
    return int(v)



def stremptynone(v):
    if v == "":
        return None
    if isinstance(v, str):
        return v
    return str(v)



def enforce_type(entry):
    types = {
        "date": (datetime.datetime, parse_date),
        "country": (str, stremptynone),
        "state": (str, stremptynone),
        "admin2": (str, stremptynone),
        "confirmed": (int, intornone),
        "deaths": (int, intornone),
        "recovered": (int, intornone)
    }

    for k, v in entry.items():
        if k not in types:
            continue

        if v is not None and not isinstance(v, types[k][0]):
            entry[k] = types[k][1](v)

    for f, (t, cons) in types.items():
        if f not in entry:
            entry[f] = cons(None)

    return entry



def import_daily(cur, f):
    if not f.endswith(".csv"):
        print("Ignoring not CSV file:", f, file=sys.stderr)
        return

    print("Processing file:", f)

    with open(f, encoding="utf-8-sig") as fp:
        reader = csv.DictReader(fp)
        for line in reader:
            line = remapfields(line)
            line = enforce_type(line)

            try:
                cur.execute("""INSERT INTO daily_report
                        (date, country, state, admin2, confirmed, deaths, recovered)
                    VALUES (:date, :country, :state, :admin2, :confirmed, :deaths, :recovered)""", line)
            except sqlite3.IntegrityError:
                cur.execute("""SELECT confirmed, deaths, recovered
                    FROM daily_report
                    WHERE date=:date AND country=:country
                        AND state=:state AND admin2=:admin2""", line)
                c, d, r = cur.fetchone()
                if c != line['confirmed'] or d != line['deaths'] or r != line['recovered']:
                    print("Inconsistency found")
                    print(line)
                    print(c, d, r)



def main():
    if len(sys.argv) != 2:
        print("usage: %s dailydir" % sys.argv[0], file=sys.stderr)
        return

    dailydir = sys.argv[1]

    cnx = db.new_connection()
    cur = cnx.cursor()
    db.create_tables(cur)

    for f in sorted(glob.glob(dailydir + "/*.csv")):
        import_daily(cur, f)
        cnx.commit()

    cur.execute("ANALYZE")
    cnx.commit()



if __name__ == '__main__':
    main()
