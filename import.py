#!/usr/bin/env python3

import sys
import glob
import datetime
import csv

import db


def remapfields(entry):
    mapfields = {
        "Date": "date",
        "Pays": "country",
        "Infections": "confirmed",
        "Deces": "deaths",
        "Guerisons": "recovered"
    }
    for k, v in list(entry.items()):
        if k not in mapfields:
            continue
        entry[mapfields[k]] = entry[k]
        del entry[k]

    return entry



def enforce_type(entry):
    types = {
        "date": (datetime.datetime, datetime.datetime.fromisoformat),
        "country": (str, str),
        "confirmed": (int, int),
        "deaths": (int, int),
        "recovered": (int, int)
    }

    for k, v in entry.items():
        if k not in types:
            continue

        if v is not None and not isinstance(v, types[k][0]):
            entry[k] = types[k][1](v)

    return entry



def import_data(cur, f):
    def filtercomment(it):
        return (line for line in it if not line.startswith("#"))

    if not f.endswith(".csv"):
        print("Ignoring not CSV file:", f, file=sys.stderr)
        return

    print("Processing file:", f)

    with open(f) as fp:
        reader = csv.DictReader(filtercomment(fp), delimiter=';')
        for line in reader:
            line = remapfields(line)
            line = enforce_type(line)

            cur.execute("""INSERT INTO daily_update
                    (date, country, confirmed, deaths, recovered)
                VALUES (:date, :country, :confirmed, :deaths, :recovered)""", line)



def main():
    if len(sys.argv) != 2:
        print("usage: %s datadir" % sys.argv[0], file=sys.stderr)
        return

    datadir = sys.argv[1]

    cnx = db.new_connection()
    cur = cnx.cursor()
    db.create_tables(cur)

    for f in sorted(glob.glob(datadir + "/*.csv")):
        import_data(cur, f)
        cnx.commit()

    cur.execute("ANALYZE")
    cnx.commit()



if __name__ == '__main__':
    main()
