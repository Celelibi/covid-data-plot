set output figfile
set title "Métrique des modèles"
set xlabel "Date"
set ylabel "MSE"

fmt = "%Y-%m-%d %H:%M:%S"
set timefmt fmt
set xdata time

set style data linespoints
set log y

plot for [i=1:|filenames|] filenames[i] using 1:5 title sprintf("%s: exp model", countries[i]),\
     for [i=1:|filenames|] filenames[i] using 1:6 title sprintf("%s: sigmoid model", countries[i])
