****************************************************
* step4_panels.do
* Input  : output/panel_[level].parquet
*            e.g. panel_firm_year.parquet
* Output : output/panel_[level].dta
*            e.g. panel_firm_year.dta
****************************************************

do "config.do"

****************************************************
* Load parquet  (requires: ssc install parquet)
****************************************************

pq use "$DATA_OUTPUT/panel_firm_year.parquet", clear

xtset firm_id year

****************************************************
* Construct variables
****************************************************

* log transform
* gen log_var = log(var + 1)

* lag / lead
* gen lag_var = L.var
* gen lead_var = F.var

* within-group demeaning
* egen var_mean = mean(var), by(firm_id)
* gen var_dm = var - var_mean

* winsorize
* winsor2 var, cuts(1 99) replace

* standardize
* egen var_std = std(var)

****************************************************
* Label variables
****************************************************

* label variable var       "Variable label"
* label variable log_var   "Log of variable"
* label variable lag_var   "Lagged variable (t-1)"

****************************************************
* Summarize
****************************************************

describe
summarize
xtsum firm_id year

****************************************************
* Save
* Naming convention: output/panel_[level].dta
*   e.g. panel_firm_year.dta
****************************************************

save "$DATA_OUTPUT/panel_firm_year.dta", replace
* pq save "$DATA_OUTPUT/panel_firm_year.parquet", replace
