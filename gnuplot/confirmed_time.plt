set output figbasename.".png"
set title "Nombre de cas confirmés"
set xlabel "Date"
set ylabel "Cas confirmés"

fmt = "%Y-%m-%d %H:%M:%S"
set timefmt fmt
set xdata time

set style data linespoints

plot for [i=1:|filenames|] filenames[i] using 1:3 title countries[i]
