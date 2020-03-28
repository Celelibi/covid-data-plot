set title "Nombre de cas confirmés"
set xlabel "Date"
set ylabel "Cas confirmés"

fmt = "%Y-%m-%d %H:%M:%S"
set timefmt fmt
set xdata time

set style data linespoints

plot conf_fit_fr using 1:3 title "France", \
              '' using 1:4 with line title "Exp France", \
              '' using 1:5 with line title "Sigmoid France", \
     conf_fit_ch using 1:3 title "Chine" ,\
              '' using 1:4 with line title "Exp Chine", \
              '' using 1:5 with line title "Sigmoid Chine"
