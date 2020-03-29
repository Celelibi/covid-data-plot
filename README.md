# Tests sur les stats du COVID-19
## Usage
Crée une base de données sqlite.

    $ ./import.py data

Voir les options.

    $ ./plot.py --help
    usage: plot.py [-h] [-f FIGDIR] [-g GNUPLOTDIR] [-t TMPDIR] [-l] [-c COUNTRY]
    
    Plot the statistics
    
    optional arguments:
      -h, --help            show this help message and exit
      -f FIGDIR, --figdir FIGDIR
                            Directory where to store the output figures (default:
                            fig)
      -g GNUPLOTDIR, --gnuplotdir GNUPLOTDIR
                            Directory where the gnuplot scripts are located
                            (default: gnuplot)
      -t TMPDIR, --tmpdir TMPDIR
                            Directory where to store the temporary data files
                            (default to system temporary directory)
      -l, --list            List available countries and exit
      -c COUNTRY, --country COUNTRY
                            Countries to plot

Sans option -c, trace par défaut les données pour la France et la Chine. Les
figures crées sont dans le dossier `fig`.

    $ ./plot.py
    $ ls fig
    confirmed_fit_time.png
    confirmed_model_metrics_anim.gif
    confirmed_model_metrics_anim.png
    confirmed_model_metrics.png
    confirmed_time.png
    diff_confirmed_confirmed.png
    diff_confirmed_time.png
