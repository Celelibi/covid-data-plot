set terminal gif size 800,600 animate delay 50
set output figfile[:strstrt(figfile, ".png")]."gif"

set xlabel "Date"
fmt = "%Y-%m-%d %H:%M:%S"
set timefmt fmt

min(a, b) = (a < b) ? a : b
max(a, b) = (a > b) ? a : b

# Find the global min and max to avoid the axis stretching between frames
stats filenames[1] using (timecolumn(1, fmt)) nooutput
xmin = STATS_min
xmax = STATS_max
stats filenames[1] using 3 nooutput
ymin = STATS_min
ymax = STATS_max

do for [i=1:nframes] {
	stats filenames[i] using (timecolumn(1, fmt)) nooutput
	xmin = min(xmin, STATS_min)
	xmax = max(xmax, STATS_max)
	stats filenames[i] using 3 nooutput
	ymin = min(ymin, STATS_min)
	ymax = max(ymax, STATS_max)
}

stats filenames[metricsidx] using 5 nooutput
ymin_metrics = STATS_min
ymax_metrics = STATS_max
do for [i=metricsidx:|filenames|] {
	stats filenames[i] using 5 nooutput
	ymin_metrics = min(ymin_metrics, STATS_min)
	ymax_metrics = max(ymax_metrics, STATS_max)
	stats filenames[i] using 6 nooutput
	ymin_metrics = min(ymin_metrics, STATS_min)
	ymax_metrics = max(ymax_metrics, STATS_max)
}

set xrange [xmin:xmax]
# "set xdata time" cannot be set before the stats commands
set xdata time

set style data linespoints

# Just a few shorthands
lastfile(countryidx) = filenames[countrieslastidx[countryidx]]
chooselt(istest, num) = (istest != 0) ? 0 : num

do for [frame=1:nframes] {
	set multiplot layout 2, 1
	ndc = ndonecountries[frame]
	curcountry = countries[ndc + 1]
	newlt = ndc * 3

	# Plot the data and the models
	set title "Nombre de cas confirmés"
	set ylabel "Cas confirmés"
	set yrange [ymin*0.8:ymax*1.2]
	unset log

	if (ndc < 1) {
		plot filenames[frame] using 1:3:(chooselt($4, newlt+1)) lt newlt+1 lc var title sprintf("%s: datapoint", curcountry),\
		                   '' using 1:5 lt newlt+2 with line title sprintf("%s: exp model", curcountry),\
		                   '' using 1:6 lt newlt+3 with line title sprintf("%s: sigmoid model", curcountry)
	} else {
		plot for [i=1:ndc] lastfile(i) using 1:3:(chooselt($4, 3*(i-1)+1)) lt 3*(i-1)+1 lc var title sprintf("%s: datapoint", countries[i]),\
		     for [i=1:ndc] lastfile(i) using 1:5 lt 3*(i-1)+2 with line title sprintf("%s: exp model", countries[i]),\
		     for [i=1:ndc] lastfile(i) using 1:6 lt 3*(i-1)+3 with line title sprintf("%s: sigmoid model", countries[i]),\
		     filenames[frame] using 1:3:(chooselt($4, newlt+1)) lt newlt+1 lc var title sprintf("%s: datapoint", curcountry),\
		                   '' using 1:5 lt newlt+2 with line title sprintf("%s: exp model", curcountry),\
		                   '' using 1:6 lt newlt+3 with line title sprintf("%s: sigmoid model", curcountry)
	}


	# Plot the models metrics
	set title "Prediction score"
	set ylabel "MSE"
	set yrange [ymin_metrics*0.8:ymax_metrics*1.2]
	set log y


	metricscuridx = metricsidx + ndc
	metricscurfile = filenames[metricscuridx]
	if (ndc < 1) {
		npoints = frame - 1
		plot metricscurfile every ::::npoints using 1:5 lt newlt+2 title sprintf("%s: exp model", curcountry),\
		                 '' every ::::npoints using 1:6 lt newlt+3 title sprintf("%s: sigmoid model", curcountry)
	} else {
		npoints = frame - countrieslastidx[ndc] - 1
		plot for [i=1:ndc] filenames[metricsidx+i-1] using 1:5 lt 3*(i-1)+2 title sprintf("%s: exp model", countries[i]),\
		     for [i=1:ndc] filenames[metricsidx+i-1] using 1:6 lt 3*(i-1)+3 title sprintf("%s: sigmoid model", countries[i]),\
		     metricscurfile every ::::npoints using 1:5 lt newlt+2 title sprintf("%s: exp model", curcountry),\
		                 '' every ::::npoints using 1:6 lt newlt+3 title sprintf("%s: sigmoid model", curcountry)
	}

	unset multiplot
}
