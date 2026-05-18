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
                     vce(cluster gvkey#cohort_id) noconstant) ///
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
