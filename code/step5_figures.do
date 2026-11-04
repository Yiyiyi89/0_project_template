****************************************************
* step5_figures.do
* Input  : output/panel_[level].dta
*            e.g. panel_firm_year.dta
* Output : tables_and_figures/figure_[des].png
*            e.g. figure_trend_var.png
*                 figure_event_study.png
****************************************************

do "config.do"

****************************************************
* Load
****************************************************

use "$DATA_OUTPUT/panel_firm_year.dta", clear

xtset firm_id year

****************************************************
* Figures
* Naming convention: tables_and_figures/figure_[des].png
*   e.g. figure_trend_var.png
*        figure_scatter_x_y.png
*        figure_event_study.png
****************************************************

* ----- time trend -----
* collapse (mean) var, by(year)
* twoway line var year, ///
*     xtitle("Year") ytitle("Mean var") ///
*     title("Trend of var")
* graph export "$DATA_RESULTS/figure_trend_var.png", replace width(1200)

* ----- scatter -----
* twoway scatter y x, msize(small) ///
*     xtitle("x") ytitle("y")
* graph export "$DATA_RESULTS/figure_scatter_x_y.png", replace width(1200)

* ----- event study -----
* eventdd y controls, timevar(event_time) ///
*     leads(5) lags(5) absorb(firm_id year) cluster(firm_id)
* graph export "$DATA_RESULTS/figure_event_study.png", replace width(1200)
