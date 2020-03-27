set title "Nombre de cas confirmés"
set xlabel "Date"
set ylabel "Cas confirmés"

fmt = "%Y-%m-%d %H:%M:%S"
set timefmt fmt
set xdata time

set style data linespoints

plot conf_time_fr using 1:3 title "France", \
     conf_time_ch using 1:3 title "Chine"
