#!/usr/bin/env python3

import os
import contextlib
import subprocess
import tempfile
import sklearn.preprocessing as skprep
import pandas as pd
import numpy as np
import scipy as sp
import scipy.optimize
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

            if cur is not None:
                it = cur.execute(datasource, params)
            else:
                it = datasource

            cnt = 0
            for row in it:
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



def exp(X, a, b):
    return np.exp(a*X+b)



def sigma(X, a, b, c):
    return c / (1.0 + exp(X, -a, -b))



def dataframe_fit(cnx, country="France"):
    params = {'country': country}

    sql = """
        SELECT date, confirmed
        FROM daily_update
        WHERE country=:country
        ORDER BY date
    """
    df = pd.read_sql_query(sql, cnx, params=params, parse_dates=["date"])
    X = df["date"].to_numpy().astype(np.float64)
    Y = df["confirmed"]

    scaler = skprep.StandardScaler()
    X = scaler.fit_transform(X.reshape(-1, 1)).reshape(-1)

    poptexp, _ = sp.optimize.curve_fit(exp, X, Y)
    df["expmodel"] = exp(X, *poptexp)
    poptsig, _ = sp.optimize.curve_fit(sigma, X, Y, p0=[1.0, 1.0, Y.max()])
    df["sigmoidmodel"] = sigma(X, *poptsig)

    return df, scaler, poptexp, poptsig



def plot_regression(cnx):
    dffr, *_ = dataframe_fit(cnx, "France")
    dfch, *_ = dataframe_fit(cnx, "Chine")

    datasource = {
        'conf_fit_fr': dffr.itertuples(index=False),
        'conf_fit_ch': dfch.itertuples(index=False)
    }

    plot(None, datasource, "confirmed_fit_time")



def main():
    cnx = db.new_connection()
    cur = cnx.cursor()
    plot_raw_data(cur)
    plot_regression(cnx)

    cur.execute("PRAGMA optimize")



if __name__ == '__main__':
    main()
