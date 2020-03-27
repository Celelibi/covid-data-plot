set title "Nouveaux cas confirmés dans le temps"
set xlabel "Date"
set ylabel "Nouveaux cas"

fmt = "%Y-%m-%d %H:%M:%S"
set timefmt fmt
set xdata time

set style data linespoints

plot conf_time_fr using 1:3 title "France", \
     conf_time_ch using 1:3 title "Chine"
