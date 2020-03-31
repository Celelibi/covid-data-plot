set output figfile
set title "Nouveaux cas par cas confirmé"
set xlabel "Cas confirmés"
set ylabel "Nouveaux cas"

set style data linespoints

plot for [i=1:|filenames|] filenames[i] using 1:2 title countries[i]
