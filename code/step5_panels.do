****************************************************
* step4_panels.do
* Input  : data/processed/panel_fm_qt_mkt.parquet (firm x quarter x market)
* Output : data/processed/panel_fm_qt.dta         (firm-quarter, treated+control)
*          data/processed/panel_main.dta          (analysis sample, winsorized)
*          data/processed/panel_main_stacked.dta  (stacked DiD, +/-4 quarters)
*
* Treatment : first quarter the firm appeared in any Polymarket market
*             (absorbing treatment). Treated firms = 820; controls = ~9000.
*
* Outcomes (Y, voluntary disclosure response from WRDS):
*   n_conf_calls     - conference calls in firm-quarter
*   n_earnings_call  - earnings calls (subset)
*   ln_conf_calls    - log(1 + n_conf_calls)
*   ln_earnings_call - log(1 + n_earnings_call)
*   i_has_call       - any conference call (extensive margin)
*   frac_earnings    - share of calls that are earnings calls
****************************************************

do "config.do"

****************************************************
* 1. Load market-level panel and collapse to firm-quarter
****************************************************
pq use "$DATA_PROCESSED/panel_fm_qt_mkt.parquet", clear

destring gvkey, replace

* indicator: firm-quarter has at least one active market
gen i_has_market = !missing(market_id)

* numeric time variable (calendar quarter, integer)
gen qt = year * 4 + quarter - 1

* Collapse firm-quarter-market to firm-quarter
*   - market activity: max/count/sum across markets in that quarter
*   - firm-quarter financials: first (constant within firm-quarter)
collapse                                                                 ///
    (max)   i_has_market i_treated_firm                                  ///
    (max)   i_resolved_anymkt = i_resolved                               ///
    (max)   mentioned_ceo_anymkt = mentioned_ceo                         ///
    (min)   best_match_tier = match_tier                                 ///
    (count) n_markets = market_id                                        ///
    (sum)   total_volume = volume_num                                    ///
    (mean)  mean_volume = volume_num                                     ///
    (first) conm size leverage roa mtb sale_growth loss rd_int cfo       ///
            tangibility atq saleq niq mkvaltq                            ///
            n_conf_calls n_earnings_call                                 ///
            ceo_name_wrds gender age tenure_years salary bonus tdc1      ///
    , by(gvkey year quarter qt)

* Treatment timing: first quarter the firm appears with any market
gen tmp_qt_treat = qt if i_has_market == 1
bys gvkey: egen qt_first_market = min(tmp_qt_treat)
drop tmp_qt_treat

* Indicator: firm was ever treated
gen treated_firm = !missing(qt_first_market)

* TWFE treatment dummy (current panel — switching treatment, used for robustness)
gen D_active = i_has_market

* Absorbing treatment dummy (used for staggered/stacked DiD)
gen D_post = treated_firm & (qt >= qt_first_market)

* Outcomes (voluntary disclosure)
gen ln_conf_calls    = ln(1 + n_conf_calls)
gen ln_earnings_call = ln(1 + n_earnings_call)
gen i_has_call       = n_conf_calls > 0
gen frac_earnings    = cond(n_conf_calls > 0, n_earnings_call / n_conf_calls, .)

* Sample window
keep if inrange(year, 2020, 2025)

* xtset for L. operator
xtset gvkey qt

do "label_variables.do"

save "$DATA_PROCESSED/panel_fm_qt.dta", replace

****************************************************
* 2. Build analysis sample (panel_main): drop missing controls, winsorize
****************************************************
use "$DATA_PROCESSED/panel_fm_qt.dta", clear

local firm_controls size leverage roa mtb sale_growth loss

* Lagged controls
sort gvkey qt
foreach v of local firm_controls {
    by gvkey: gen `v'_lag1 = `v'[_n-1] if qt == qt[_n-1] + 1
}

* Winsorize ratios at 1/99
local winvars leverage_lag1 roa_lag1 mtb_lag1 sale_growth_lag1
foreach v of local winvars {
    capture winsor2 `v', cuts(1 99) replace
}

* Drop obs missing core firm controls
foreach v of local firm_controls {
    drop if missing(`v'_lag1)
}

* Apply variable labels
do "label_variables.do"

save "$DATA_PROCESSED/panel_main.dta", replace

****************************************************
* 3. Build stacked DiD panel
*    For each cohort g (first-mention quarter):
*      - Treated:  firms with qt_first_market == g
*      - Controls: firms not yet treated within [g-W, g+W]
*                   (qt_first_market > g+W) OR never-treated
*      - Event window: qt in [g-W, g+W]
*    W = 4 quarters (1 year on each side) — fits 24-quarter panel
****************************************************
use "$DATA_PROCESSED/panel_main.dta", clear

local W = 4
save "$DATA_TEMP/_stacking_raw.dta", replace

levelsof qt_first_market, local(cohorts)

foreach g of local cohorts {
    di "*** Building stack for cohort g = `g' ***"
    use "$DATA_TEMP/_stacking_raw.dta", clear

    local lo = `g' - `W'
    local hi = `g' + `W'

    keep if (qt_first_market == `g') ///
         | (qt_first_market > `hi')  ///
         | missing(qt_first_market)

    keep if inrange(qt, `lo', `hi')

    gen cohort  = `g'
    gen treated = (qt_first_market == `g')

    save "$DATA_TEMP/_stacking_`g'.dta", replace
}

clear
foreach g of local cohorts {
    append using "$DATA_TEMP/_stacking_`g'.dta"
}
sort cohort treated gvkey qt

* Cohort id
egen cohort_id = group(cohort)

* Relative time and event-time dummies (baseline t = -1)
gen rt   = qt - cohort
gen post = (rt >= 0)
gen D    = treated * post

forvalues k = `W'(-1)2 {
    gen D_pre`k' = treated * (rt == -`k')
}
gen D_post0 = treated * (rt == 0)
forvalues k = 1/`W' {
    gen D_post`k' = treated * (rt == `k')
}

* time_to_treat for eventdd (missing for controls so eventdd ignores them)
gen time_to_treat = rt if treated == 1
replace time_to_treat = . if treated == 0

do "label_variables.do"

save "$DATA_PROCESSED/panel_main_stacked.dta", replace
di "Stacked panel saved: $DATA_PROCESSED/panel_main_stacked.dta"

* Clean up temp stacks
foreach g of local cohorts {
    capture erase "$DATA_TEMP/_stacking_`g'.dta"
}
capture erase "$DATA_TEMP/_stacking_raw.dta"
