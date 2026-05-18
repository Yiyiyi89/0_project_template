****************************************************
* step5_figures.do — Event-study figures + robustness
*
* Treatment: D_post (absorbing).
* Cohort:    cohort = qt_first_market (calendar quarter of first mention).
* Window:    W = 4 quarters on each side.
*
* Figures (one per Y in Y_LIST + LOO/HonestDiD/FECT robustness for primary Y):
*   stacked_did_<Y>.png       — event study via eventdd (one per Y)
*   loo_cohort_<Y_PRIM>.png   — leave-one-cohort-out for primary Y
*   honestdid_<Y_PRIM>.png    — Honest DiD bounds for primary Y
*   <Y_PRIM>_fect_ife.png     — FECT with interactive FE
*   <Y_PRIM>_fect_placebo.png — FECT placebo test
****************************************************

do "config.do"

global firm_controls size_lag1 leverage_lag1 roa_lag1 mtb_lag1 sale_growth_lag1 loss_lag1
global Y_LIST        n_conf_calls n_earnings_call ln_conf_calls ln_earnings_call i_has_call frac_earnings
global Y_PRIM        n_conf_calls


****************************************************
* Event study (eventdd) for each Y
****************************************************
foreach Y of global Y_LIST {
    use "$DATA_PROCESSED/panel_main_stacked.dta", clear
    do "label_variables.do"

    capture noisily eventdd `Y' $firm_controls, ///
        timevar(time_to_treat) ///
        method(hdfe, absorb(gvkey#cohort_id qt#cohort_id) ///
                     vce(cluster gvkey#cohort_id)) ///
        leads(4) lags(4) ///
        baseline(-1) level(95) ///
        graph_op( ///
            ytitle("Coefficient (baseline: t = -1)") ///
            xtitle("Quarters relative to first market mention") ///
            graphregion(color(white)) legend(off) ///
        )
    if _rc == 0 {
        graph export "$OUTPUT_FIGURES/stacked_did_`Y'.png", replace width(1400)
    }
}


****************************************************
* Leave-one-cohort-out robustness (primary Y only)
****************************************************
use "$DATA_PROCESSED/panel_main_stacked.dta", clear
do "label_variables.do"

levelsof cohort_id, local(cohorts)

postfile handle double(cohort_dropped event_time coef se) ///
    using "$DATA_PROCESSED/loo_cohort_results.dta", replace

foreach c of local cohorts {
    di "Dropping cohort: `c'"
    capture noisily reghdfe $Y_PRIM $firm_controls ///
        D_pre4 D_pre3 D_pre2 D_post0 D_post1 D_post2 D_post3 D_post4 ///
        if cohort_id != `c', ///
        absorb(gvkey#cohort_id qt#cohort_id) vce(cluster gvkey#cohort_id)

    if _rc == 0 {
        forvalues t = 4(-1)2 {
            capture local b = _b[D_pre`t']
            if _rc == 0 {
                local s = _se[D_pre`t']
                post handle (`c') (-`t') (`b') (`s')
            }
        }
        post handle (`c') (-1) (0) (0)
        forvalues t = 0/4 {
            capture local b = _b[D_post`t']
            if _rc == 0 {
                local s = _se[D_post`t']
                post handle (`c') (`t') (`b') (`s')
            }
        }
    }
}
postclose handle

use "$DATA_PROCESSED/panel_main_stacked.dta", clear
reghdfe $Y_PRIM $firm_controls ///
    D_pre4 D_pre3 D_pre2 D_post0 D_post1 D_post2 D_post3 D_post4, ///
    absorb(gvkey#cohort_id qt#cohort_id) vce(cluster gvkey#cohort_id)

postfile handle_full double(cohort_dropped event_time coef se) ///
    using "$DATA_PROCESSED/loo_cohort_full.dta", replace
forvalues t = 4(-1)2 {
    local b = _b[D_pre`t']
    local s = _se[D_pre`t']
    post handle_full (0) (-`t') (`b') (`s')
}
post handle_full (0) (-1) (0) (0)
forvalues t = 0/4 {
    local b = _b[D_post`t']
    local s = _se[D_post`t']
    post handle_full (0) (`t') (`b') (`s')
}
postclose handle_full

use "$DATA_PROCESSED/loo_cohort_results.dta", clear
append using "$DATA_PROCESSED/loo_cohort_full.dta"

preserve
use "$DATA_PROCESSED/panel_main_stacked.dta", clear
distinct gvkey
local n_clusters = r(ndistinct)
restore

local df = `n_clusters' - 1
local t_crit = invttail(`df', 0.025)

gen ci_lo = coef - `t_crit' * se
gen ci_hi = coef + `t_crit' * se
gen full = (cohort_dropped == 0)

twoway ///
    (line coef event_time if full == 0, connect(ascending) lcolor(gs12%85) lwidth(vthin)) ///
    (rarea ci_lo ci_hi event_time if full == 1, color(navy%15) lwidth(none)) ///
    (connected coef event_time if full == 1, mcolor(navy) msymbol(circle) msize(small) ///
        lcolor(navy) lpattern(solid) lwidth(medthick)), ///
    xline(-1, lcolor(gs8) lpattern(dash)) ///
    yline(0, lcolor(gs10) lpattern(solid) lwidth(vthin)) ///
    ytitle("Coefficient (baseline: t = -1)") ///
    xtitle("Quarters relative to first market mention") ///
    xlabel(-4(1)4) ///
    legend(order(3 "Full sample" 2 "95% CI" 1 "Leave-one-cohort-out") ///
           rows(1) size(small) position(6) ring(1)) ///
    graphregion(color(white)) ///
    title("Leave-One-Cohort-Out Robustness", size(medium))

graph export "$OUTPUT_FIGURES/loo_cohort_$Y_PRIM.png", replace width(1400)


****************************************************
* Honest DiD (Borusyak et al. 2024) — primary Y only
****************************************************
use "$DATA_PROCESSED/panel_main_stacked.dta", clear
do "label_variables.do"

capture rename D_pre1 D_baseline
reghdfe $Y_PRIM D_pre* D_post* $firm_controls, ///
    absorb(gvkey#cohort_id qt#cohort_id) ///
    vce(cluster gvkey#cohort_id) noconstant

capture noisily honestdid, pre(1/3) post(4) mvec(0.05(0.05)1.5) delta(rm) ///
    coefplot xlabel(, angle(90))
if _rc == 0 {
    graph export "$OUTPUT_FIGURES/honestdid_$Y_PRIM.png", replace width(1400)
}


****************************************************
* FECT (interactive FE) — primary Y only
****************************************************
use "$DATA_PROCESSED/panel_main.dta", clear
do "label_variables.do"

capture noisily fect $Y_PRIM, treat(D_post) unit(gvkey) time(qt) ///
    cov($firm_controls) method(ife) force(two-way) ///
    se nboots(200)
if _rc == 0 {
    graph export "$OUTPUT_FIGURES/${Y_PRIM}_fect_ife.png", replace width(1400)
}

capture noisily fect $Y_PRIM, treat(D_post) unit(gvkey) time(qt) ///
    cov($firm_controls) method(ife) force(two-way) ///
    se nboots(200) placeboTest
if _rc == 0 {
    graph export "$OUTPUT_FIGURES/${Y_PRIM}_fect_placebo.png", replace width(1400)
}
