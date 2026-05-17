****************************************************
* step5_figures.do
* Input  : data/processed/panel_[level].dta
*            e.g. panel_firm_year.dta
* Output : output/figures/figure_[des].png
*            e.g. figure_trend_var.png
*                 figure_event_study.png
****************************************************

do "config.do"

****************************************************
* Load
****************************************************

use "$DATA_PROCESSED/panel_firm_year.dta", clear

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
* graph export "$OUTPUT_FIGURES/figure_trend_var.png", replace width(1200)

* ----- scatter -----
* twoway scatter y x, msize(small) ///
*     xtitle("x") ytitle("y")
* graph export "$OUTPUT_FIGURES/figure_scatter_x_y.png", replace width(1200)

* ----- event study -----
* eventdd y controls, timevar(event_time) ///
*     leads(5) lags(5) absorb(firm_id year) cluster(firm_id)
* graph export "$OUTPUT_FIGURES/figure_event_study.png", replace width(1200)
