set output figbasename.".png"
set title "Nombre de cas confirmés"
set xlabel "Date"
set ylabel "Cas confirmés"

maxy = 0
do for [i=1:|filenames|] {
	stats filenames[i] using 3 nooutput
	maxy = (STATS_max > maxy) ? STATS_max : maxy
}
set yrange [:maxy*1.2]

fmt = "%Y-%m-%d %H:%M:%S"
set timefmt fmt
set xdata time

set style data linespoints

plot for [i=1:|filenames|] filenames[i] using 1:3 title countries[i],\
     for [i=1:|filenames|] filenames[i] using 1:4 with line title sprintf("%s: exp model", countries[i]),\
     for [i=1:|filenames|] filenames[i] using 1:5 with line title sprintf("%s: sigmoid model", countries[i])
