#!/usr/bin/env python3

import os
import contextlib
import subprocess
import tempfile
import config
import db


def plot(cur, datasource, name, params={}):
    # Make the possibly missing directories
    if config.tmpdir:
        os.makedirs(config.tmpdir, exist_ok=True)
    os.makedirs(config.figdir, exist_ok=True)

    # Make the file path from the configured path
    gnuplotinc = os.path.join(config.gnuplotdir, "common.plt")
    figfile = os.path.join(config.figdir, "%s.png" % name)
    gnuplotfile = os.path.join(config.gnuplotdir, "%s.plt" % name)

    gnuplotcmd = ["gnuplot", "-d"]
    gnuplotcmd += ["-e", 'load "%s"' % gnuplotinc]
    gnuplotcmd += ["-e", 'set output "%s"' % figfile]

    with contextlib.ExitStack() as exitstack:
        for dataname, datasource in datasource.items():
            datafp = tempfile.NamedTemporaryFile("w+", dir=config.tmpdir)
            exitstack.enter_context(datafp)

            cur.execute(datasource, params)
            cnt = 0
            for row in cur:
                rowstr = " ".join(str(f) for f in row)
                print(rowstr, file=datafp)
                cnt += 1

            print(cnt, "rows written")
            datafp.flush()
            gnuplotcmd += ["-e", '%s = "%s"' % (dataname, datafp.name)]

        for kv in params.items():
            gnuplotcmd += ["-e", '%s = %r' % kv]

        gnuplotcmd.append(gnuplotfile)
        subprocess.run(gnuplotcmd)




def plot_raw_data(cur):
    datasource = {
        'conf_time_fr': """
            SELECT date, confirmed
            FROM daily_update
            WHERE country='France'
            ORDER BY date
        """,
        'conf_time_ch': """
            SELECT date, confirmed
            FROM daily_update
            WHERE country='Chine'
            ORDER BY date
        """
    }
    plot(cur, datasource, "confirmed_time")

    datasource = {
        'conf_time_fr': """
            SELECT date, confirmed - lag(confirmed) OVER win
            FROM daily_update
            WHERE country='France'
            WINDOW win AS (ORDER BY date)
            ORDER BY date
        """,
        'conf_time_ch': """
            SELECT date, confirmed - lag(confirmed) OVER win
            FROM daily_update
            WHERE country='Chine'
            WINDOW win AS (ORDER BY date)
            ORDER BY date
        """
    }
    plot(cur, datasource, "diff_confirmed_time")

    datasource = {
        'conf_time_fr': """
            SELECT confirmed, confirmed - lag(confirmed) OVER win
            FROM daily_update
            WHERE country='France'
            WINDOW win AS (ORDER BY date)
            ORDER BY date
        """,
        'conf_time_ch': """
            SELECT confirmed, confirmed - lag(confirmed) OVER win
            FROM daily_update
            WHERE country='Chine'
            WINDOW win AS (ORDER BY date)
            ORDER BY date
        """
    }
    plot(cur, datasource, "diff_confirmed_confirmed")



def main():
    cnx = db.new_connection()
    cur = cnx.cursor()
    plot_raw_data(cur)

    cur.execute("PRAGMA optimize")



if __name__ == '__main__':
    main()
