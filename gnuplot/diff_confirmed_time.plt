set output figbasename.".png"
set title "Nouveaux cas confirmés dans le temps"
set xlabel "Date"
set ylabel "Nouveaux cas"

fmt = "%Y-%m-%d %H:%M:%S"
set timefmt fmt
set xdata time

set style data linespoints

plot for [i=1:|filenames|] filenames[i] using 1:3 title countries[i]
