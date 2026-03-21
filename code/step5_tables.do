****************************************************
* step5_tables.do
* Input  : output/panel_[level].dta
*            e.g. panel_firm_year.dta
* Output : tables_and_figures/table_[des].xls
*          tables_and_figures/table_[des].tex
*            e.g. table_summary_stats.xls
*                 table_baseline_reg.tex
****************************************************

do "config.do"

****************************************************
* Load
****************************************************

use "$DATA_OUTPUT/panel_firm_year.dta", clear

xtset firm_id year

****************************************************
* Summary statistics
* Naming convention: tables_and_figures/table_[des].xls/.tex
*   e.g. table_summary_stats.xls
*        table_baseline_reg.tex
****************************************************

* estpost summarize var1 var2 var3
* esttab using "$DATA_RESULTS/table_summary_stats.tex", ///
*     cells("mean(fmt(3)) sd(fmt(3)) min max count") ///
*     label noobs replace

****************************************************
* Regression tables
****************************************************

* reg y x1 x2, vce(cluster firm_id)
* eststo m1

* reghdfe y x1 x2, absorb(firm_id year) vce(cluster firm_id)
* eststo m2

* esttab m1 m2 using "$DATA_RESULTS/table_baseline_reg.tex", ///
*     label star(* 0.1 ** 0.05 *** 0.01) b(3) se(3) ar2 replace

* esttab m1 m2 using "$DATA_RESULTS/table_baseline_reg.xls", ///
*     label star(* 0.1 ** 0.05 *** 0.01) b(3) se(3) ar2 replace
