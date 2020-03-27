set title "Nouveaux cas par cas confirmé"
set xlabel "Cas confirmés"
set ylabel "Nouveaux cas"

set style data linespoints

plot conf_time_fr using 1:2 title "France", \
     conf_time_ch using 1:2 title "Chine"
