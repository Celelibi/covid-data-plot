#!/usr/bin/env python3

import os
import contextlib
import collections
import subprocess
import argparse
import tempfile
import numpy as np
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



def check_countries(cur, countries):
    countries = set(countries)

    sql = ", ".join(["(?)"]*len(countries))
    cur.execute("""WITH query(country) AS (VALUES %s)
        SELECT q.*
        FROM query AS q
            LEFT JOIN daily_update AS d
                ON (LOWER(q.country)=LOWER(d.country))
        WHERE d.country IS NULL""" % sql, sorted(countries))
    missing = set(c for c, in cur)

    if missing:
        print("Some countries are not in the database:")
        print(", ".join(sorted(missing)))
        return False

    return True



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
    gnuplotcmd += ["-e", 'figfile = "%s"' % figfile]
    gnuplotcmd += ["-e", 'set output figfile']

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
            WHERE LOWER(country)=LOWER(:country%d)
            ORDER BY date
        """ % i for i in range(len(countries))
    ]
    plot(cur, datasource, "confirmed_time", params)

    datasource = ["""
            SELECT date, confirmed - lag(confirmed) OVER win
            FROM daily_update
            WHERE LOWER(country)=LOWER(:country%d)
            WINDOW win AS (ORDER BY date)
            ORDER BY date
        """ % i for i in range(len(countries))
    ]
    plot(cur, datasource, "diff_confirmed_time", params)

    datasource = ["""
            SELECT confirmed, confirmed - lag(confirmed) OVER win
            FROM daily_update
            WHERE LOWER(country)=LOWER(:country%d)
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
    import pandas as pd

    params = {'country': country}

    sql = """
        SELECT date, confirmed
        FROM daily_update
        WHERE LOWER(country)=LOWER(:country)
        ORDER BY date
    """
    return pd.read_sql_query(sql, cnx, params=params, parse_dates=["date"])



def fit_models(X, Y, p0exp=None, p0sig=None):
    import sklearn.preprocessing as skprep
    import scipy.optimize as spopt

    scaler = skprep.StandardScaler()
    X = scaler.fit_transform(X.reshape(-1, 1)).reshape(-1)

    # Just a sane default starting point
    if p0sig is None:
        p0sig = [1.0, 1.0, -Y.max()]

    poptexp, _ = spopt.curve_fit(exp, X, Y, p0=p0exp, maxfev=10000)
    poptsig, _ = spopt.curve_fit(sigma, X, Y, p0=p0sig, maxfev=10000)

    return scaler, poptexp, poptsig



def fit(df):
    X = df["date"].to_numpy().astype(np.float64)
    Y = df["confirmed"].to_numpy()
    return fit_models(X, Y)



def simulate_models(df, scaler, poptexp, poptsig, until=None, step=None):
    import pandas as pd

    if step is None:
        step = np.timedelta64(1, "D")

    firstdate = df["date"].to_numpy().max() + step
    if until is not None and until > firstdate:
        dates = np.arange(firstdate, until, step)
        df = df.append(pd.DataFrame({"date": dates}), sort=False)

    X = df["date"].to_numpy().astype(np.float64)
    X = scaler.transform(X.reshape(-1, 1)).reshape(-1)

    df["expmodel"] = exp(X, *poptexp)
    df["sigmoidmodel"] = sigma(X, *poptsig)

    return df



def plot_regression(cnx, countries):
    oneday = np.timedelta64(1, "D")
    datasource = []
    for c in countries:
        df = get_dataframe(cnx, c)
        popt = fit(df)

        lastdate = df["date"].to_numpy().max() + oneday
        lastdate = lastdate + 30 * oneday
        fulldf = simulate_models(df, *popt, until=lastdate)

        datasource.append(fulldf.itertuples(index=False))

    params = {"countries": countries}
    plot(None, datasource, "confirmed_fit_time", params)



def metrics_evolution(cnx, country):
    import sklearn.metrics as skmetrics
    import pandas as pd

    oneday = np.timedelta64(1, "D")
    df = get_dataframe(cnx, country)
    lastdate = df["date"].to_numpy().max() + oneday
    lastdate = lastdate + 30 * oneday

    X = df["date"].to_numpy().astype(np.float64)
    Y = df["confirmed"].to_numpy()

    _, *p0 = fit_models(X, Y)
    scores = []
    dfevo = []

    minsamples = 20
    testsize = 5
    for chunksize in range(minsamples, X.shape[0] - testsize):
        # Take a chunk of the time series and keep the last 10 as test set
        Xchunk = X[:chunksize]
        Ychunk = Y[:chunksize]
        Xtrain = Xchunk[:-testsize]
        Ytrain = Ychunk[:-testsize]
        Xtest = Xchunk[-testsize:]
        Ytest = Ychunk[-testsize:]

        scaler, *popts = fit_models(Xtrain, Ytrain, *p0)
        dfchunk = df.iloc[:chunksize].copy()
        dfchunk["testset"] = 0
        dfchunk.loc[chunksize-testsize:, "testset"] = 1
        dfchunk = simulate_models(dfchunk, scaler, *popts, until=lastdate)
        dfevo.append(dfchunk)

        dfpred = dfchunk.iloc[chunksize-testsize:chunksize]
        r2exp = skmetrics.r2_score(Ytest, dfpred["expmodel"])
        r2sig = skmetrics.r2_score(Ytest, dfpred["sigmoidmodel"])
        mseexp = skmetrics.mean_squared_error(Ytest, dfpred["expmodel"])
        msesig = skmetrics.mean_squared_error(Ytest, dfpred["sigmoidmodel"])
        scores.append([df["date"][chunksize-1], r2exp, r2sig, mseexp, msesig])

    dfmetrics = pd.DataFrame(scores, columns=["date", "r2exp", "r2sig", "mseexp", "msesig"])
    return dfmetrics, dfevo



def plot_metrics_evolution(cnx, countries):
    datasource_metrics = []
    datasource_anim = []
    anim_metrics = []
    params_anim = {
        'countries': countries,
        'nframes': 0,
        'ncountries': 0,
        'countrieslastidx': [],
        'ndonecountries': []
    }
    for c in countries:
        df, dfevo = metrics_evolution(cnx, c)
        datasource_metrics.append(df.itertuples(index=False))
        datasource_anim += [f.itertuples(index=False) for f in dfevo]
        params_anim['nframes'] += len(dfevo)
        params_anim['ncountries'] += 1
        params_anim['countrieslastidx'].append(params_anim['nframes'] - 1)
        params_anim['ndonecountries'] += [params_anim['ncountries'] - 1] * len(dfevo)
        anim_metrics.append(df.itertuples(index=False))

    params_anim['metricsidx'] = len(datasource_anim) + 1
    datasource_anim += anim_metrics

    params = {"countries": countries}
    plot(None, datasource_metrics, "confirmed_model_metrics", params)
    plot(None, datasource_anim, "confirmed_model_metrics_anim", params_anim)



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
        if check_countries(cur, countries):
            plot_raw_data(cur, countries)
            plot_regression(cnx, countries)
            plot_metrics_evolution(cnx, countries)

    cur.execute("PRAGMA optimize")



if __name__ == '__main__':
    main()
