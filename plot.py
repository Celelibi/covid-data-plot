#!/usr/bin/env python3

import os
import contextlib
import collections
import subprocess
import argparse
import tempfile
import sklearn.preprocessing as skprep
import pandas as pd
import numpy as np
import scipy as sp
import scipy.optimize
import config
import db



def list_countries(cur):
    cur.execute("SELECT COUNT(DISTINCT country) FROM daily_update")
    (total,) = cur.fetchone()
    print("%d countries found" % total)

    cur.execute("SELECT MAX(LENGTH(country)) FROM daily_update")
    (maxlenc,) = cur.fetchone()
    cur.execute("""
        SELECT MAX(LENGTH(cnt))
        FROM (
            SELECT COUNT(*) AS cnt
            FROM daily_update
            GROUP BY country
        )
    """)
    (maxlenn,) = cur.fetchone()

    cur.execute("""
        SELECT country, COUNT(*)
        FROM daily_update
        GROUP BY country
        ORDER BY country
    """)
    print("Country".center(maxlenc) + " Number of data points")
    print("".ljust(maxlenc, '-') + " ---------------------")
    for country, npoints in cur:
        print(country.ljust(maxlenc), str(npoints).rjust(maxlenn))



def fill_datafiles(cur, datasource, params, fp):
    if cur is not None:
        it = cur.execute(datasource, params)
    else:
        it = datasource

    cnt = 0
    for row in it:
        rowstr = " ".join(str(f) for f in row)
        print(rowstr, file=fp)
        cnt += 1

    print(cnt, "rows written")
    fp.flush()



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

    if isinstance(datasource, collections.abc.Mapping):
        datasourceit = datasource.values()
        datanames = datasource.keys()
    else:
        datasourceit = datasource
        datanames = None

    with contextlib.ExitStack() as exitstack:
        datafpnames = []
        for dsource in datasourceit:
            datafp = tempfile.NamedTemporaryFile("w+", dir=config.tmpdir)
            exitstack.enter_context(datafp)
            datafpnames.append(datafp.name)

            fill_datafiles(cur, dsource, params, datafp)


        if datanames is not None:
            for dataname, filename in zip(datanames, datafpnames):
                gnuplotcmd += ["-e", '%s = "%s"' % (dataname, filename)]
        else:
            gnuplotcmd += ["-e", "array filenames = %r" % datafpnames]

        for k, v in params.items():
            if isinstance(v, list):
                gnuplotcmd += ["-e", 'array %s = %r' % (k, v)]
            else:
                gnuplotcmd += ["-e", '%s = %r' % (k, v)]

        gnuplotcmd.append(gnuplotfile)
        subprocess.run(gnuplotcmd)




def plot_raw_data(cur, countries):
    params = {"country%d" % i: c for i, c in enumerate(countries)}
    params["countries"] = countries

    datasource = ["""
            SELECT date, confirmed
            FROM daily_update
            WHERE country=:country%d
            ORDER BY date
        """ % i for i in range(len(countries))
    ]
    plot(cur, datasource, "confirmed_time", params)

    datasource = ["""
            SELECT date, confirmed - lag(confirmed) OVER win
            FROM daily_update
            WHERE country=:country%d
            WINDOW win AS (ORDER BY date)
            ORDER BY date
        """ % i for i in range(len(countries))
    ]
    plot(cur, datasource, "diff_confirmed_time", params)

    datasource = ["""
            SELECT confirmed, confirmed - lag(confirmed) OVER win
            FROM daily_update
            WHERE country=:country%d
            WINDOW win AS (ORDER BY date)
            ORDER BY date
        """ % i for i in range(len(countries))
    ]
    plot(cur, datasource, "diff_confirmed_confirmed", params)



def exp(X, a, b):
    return np.exp(a*X+b)



def sigma(X, a, b, c):
    return c / (1.0 + exp(X, -a, -b))



def get_dataframe(cnx, country):
    params = {'country': country}

    sql = """
        SELECT date, confirmed
        FROM daily_update
        WHERE country=:country
        ORDER BY date
    """
    return pd.read_sql_query(sql, cnx, params=params, parse_dates=["date"])



def fit_models(X, Y):
    scaler = skprep.StandardScaler()
    X = scaler.fit_transform(X.reshape(-1, 1)).reshape(-1)

    poptexp, _ = sp.optimize.curve_fit(exp, X, Y)
    poptsig, _ = sp.optimize.curve_fit(sigma, X, Y, p0=[1.0, 1.0, Y.max()])

    return scaler, poptexp, poptsig



def dataframe_fit(cnx, country):
    df = get_dataframe(cnx, country)
    X = df["date"].to_numpy().astype(np.float64)
    Y = df["confirmed"].to_numpy()

    scaler, poptexp, poptsig = fit_models(X, Y)
    X = scaler.transform(X.reshape(-1, 1)).reshape(-1)
    df["expmodel"] = exp(X, *poptexp)
    df["sigmoidmodel"] = sigma(X, *poptsig)

    return df, scaler, poptexp, poptsig



def extrapolate(days, df, scaler, poptexp, poptsig):
    day = np.timedelta64(1, "D")
    firstdate = df["date"].to_numpy().max() + day
    dates = np.arange(firstdate, firstdate + days * day, day)

    X = dates.astype(np.float64)
    X = scaler.transform(X.reshape(-1, 1)).reshape(-1)

    Yexp = exp(X, *poptexp)
    Ysig = sigma(X, *poptsig)

    columns = {
        "date": dates,
        "expmodel": Yexp,
        "sigmoidmodel": Ysig
    }
    newdf = pd.DataFrame(columns)

    return df.append(newdf, sort=False)



def plot_regression(cnx, countries):
    params = {"countries": countries}
    datasource = []
    for c in countries:
        data = dataframe_fit(cnx, c)
        fulldf = extrapolate(30, *data)
        datasource.append(fulldf.itertuples(index=False))

    plot(None, datasource, "confirmed_fit_time", params)



def main():
    parser = argparse.ArgumentParser(description="Plot the statistics")
    parser.add_argument("-f", "--figdir", help="Directory where to store the output figures (default: %s)" % config.figdir)
    parser.add_argument("-g", "--gnuplotdir", help="Directory where the gnuplot scripts are located (default: %s)" % config.gnuplotdir)
    parser.add_argument("-t", "--tmpdir", help="Directory where to store the temporary data files (default to system temporary directory)")
    parser.add_argument("-l", "--list", action='store_true', help="List available countries and exit")
    parser.add_argument("-c", "--country", action='append', help="Countries to plot")

    args = parser.parse_args()

    if args.figdir is not None:
        config.figdir = args.figdir
    if args.gnuplotdir is not None:
        congnuplot.gnuplotdir = args.gnuplotdir
    if args.tmpdir is not None:
        config.tmpdir = args.tmpdir

    if args.country is None:
        countries = ["France", "Chine"]
    else:
        countries = args.country

    cnx = db.new_connection()
    cur = cnx.cursor()

    if args.list:
        list_countries(cur)
    else:
        plot_raw_data(cur, countries)
        plot_regression(cnx, countries)

    cur.execute("PRAGMA optimize")



if __name__ == '__main__':
    main()
