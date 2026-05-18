****************************************************
* step5_tables.do — Tables for Polymarket mention -> voluntary disclosure
*
* X (treatment) : D_post (firm ever covered, post-first-mention; absorbing)
* Y_LIST        : n_conf_calls n_earnings_call ln_conf_calls
*                 ln_earnings_call i_has_call frac_earnings
*
* Tables (exploration stage — loops over Y so code stays short):
*   Table 0  : Descriptive statistics
*   Table 1  : TWFE — stepwise FE absorption, per Y
*   Table 2  : Stacked DiD — stepwise FE absorption, per Y
*   Table 3  : Stacked DiD — all outcomes summary (main spec)
*   Table 4  : Heterogeneity by match_tier
*   Table 5  : Heterogeneity by mentioned_ceo
*   Table 6  : Heterogeneity by market volume
*   Table 7  : TWFE switching-treatment (pulsed) robustness
****************************************************

do "config.do"

global firm_controls size_lag1 leverage_lag1 roa_lag1 mtb_lag1 sale_growth_lag1 loss_lag1
global Y_LIST        n_conf_calls n_earnings_call ln_conf_calls ln_earnings_call i_has_call frac_earnings


****************************************************
* Table 0: Descriptive Statistics
****************************************************
use "$DATA_PROCESSED/panel_main_stacked.dta", clear
do "label_variables.do"

preserve
    bysort gvkey qt: keep if _n == 1
    local desc_vars D_post $Y_LIST $firm_controls
    outreg2 using "$OUTPUT_TABLES/desc_stats.xls", ///
        replace excel sum(log) keep(`desc_vars') sortvar(`desc_vars') ///
        eqkeep(N mean sd min max) label dec(3)
restore


****************************************************
* Table 1: TWFE stepwise FE — one xls per Y
****************************************************
foreach Y of global Y_LIST {
    use "$DATA_PROCESSED/panel_main.dta", clear
    do "label_variables.do"

    local outfile "$OUTPUT_TABLES/twfe_`Y'.xls"
    local first 1

    foreach spec in "noctrl" "ctrl" "fe_firm" "fe_qt" "fe_both" {

        if "`spec'" == "noctrl" {
            local ftxt Firm Controls, No, Firm FE, No, Quarter FE, No
            capture noisily regress `Y' D_post, vce(cluster gvkey)
        }
        else if "`spec'" == "ctrl" {
            local ftxt Firm Controls, Yes, Firm FE, No, Quarter FE, No
            capture noisily regress `Y' D_post $firm_controls, vce(cluster gvkey)
        }
        else if "`spec'" == "fe_firm" {
            local ftxt Firm Controls, Yes, Firm FE, Yes, Quarter FE, No
            capture noisily reghdfe `Y' D_post $firm_controls, absorb(gvkey) vce(cluster gvkey)
        }
        else if "`spec'" == "fe_qt" {
            local ftxt Firm Controls, Yes, Firm FE, No, Quarter FE, Yes
            capture noisily reghdfe `Y' D_post $firm_controls, absorb(qt) vce(cluster gvkey)
        }
        else if "`spec'" == "fe_both" {
            local ftxt Firm Controls, Yes, Firm FE, Yes, Quarter FE, Yes
            capture noisily reghdfe `Y' D_post $firm_controls, absorb(gvkey qt) vce(cluster gvkey)
        }

        if _rc == 0 {
            local cmd = cond(`first', "replace", "append")
            outreg2 using "`outfile'", excel `cmd' dec(3) label nocon keep(D_post) ///
                ctitle("`:variable label `Y''") addtext(`ftxt')
            local first 0
        }
    }
}


****************************************************
* Table 2: Stacked DiD stepwise FE — one xls per Y
****************************************************
foreach Y of global Y_LIST {
    use "$DATA_PROCESSED/panel_main_stacked.dta", clear
    do "label_variables.do"

    local outfile "$OUTPUT_TABLES/stacked_did_`Y'.xls"
    local first 1

    foreach spec in "noctrl" "ctrl" "fe_firm" "fe_qt" "fe_both" {

        if "`spec'" == "noctrl" {
            local ftxt Firm Controls, No, Firm x Cohort FE, No, Quarter x Cohort FE, No
            capture noisily regress `Y' D, vce(cluster gvkey)
        }
        else if "`spec'" == "ctrl" {
            local ftxt Firm Controls, Yes, Firm x Cohort FE, No, Quarter x Cohort FE, No
            capture noisily regress `Y' D $firm_controls, vce(cluster gvkey)
        }
        else if "`spec'" == "fe_firm" {
            local ftxt Firm Controls, Yes, Firm x Cohort FE, Yes, Quarter x Cohort FE, No
            capture noisily reghdfe `Y' D $firm_controls, absorb(gvkey#cohort_id) vce(cluster gvkey)
        }
        else if "`spec'" == "fe_qt" {
            local ftxt Firm Controls, Yes, Firm x Cohort FE, No, Quarter x Cohort FE, Yes
            capture noisily reghdfe `Y' D $firm_controls, absorb(qt#cohort_id) vce(cluster gvkey)
        }
        else if "`spec'" == "fe_both" {
            local ftxt Firm Controls, Yes, Firm x Cohort FE, Yes, Quarter x Cohort FE, Yes
            capture noisily reghdfe `Y' D $firm_controls, ///
                absorb(gvkey#cohort_id qt#cohort_id) vce(cluster gvkey#cohort_id)
        }

        if _rc == 0 {
            local cmd = cond(`first', "replace", "append")
            outreg2 using "`outfile'", excel `cmd' dec(3) label nocon keep(D) ///
                ctitle("`:variable label `Y''") addtext(`ftxt')
            local first 0
        }
    }
}


****************************************************
* Table 3: Stacked DiD — all outcomes (main spec)
****************************************************
use "$DATA_PROCESSED/panel_main_stacked.dta", clear
do "label_variables.do"

local outfile  "$OUTPUT_TABLES/stacked_did_all_outcomes.xls"
local addfe    Firm Controls, Yes, Firm x Cohort FE, Yes, Quarter x Cohort FE, Yes
local first 1

foreach Y of global Y_LIST {
    capture noisily reghdfe `Y' D $firm_controls, ///
        absorb(gvkey#cohort_id qt#cohort_id) vce(cluster gvkey#cohort_id)
    if _rc == 0 {
        local cmd = cond(`first', "replace", "append")
        outreg2 using "`outfile'", excel `cmd' dec(3) label nocon keep(D) ///
            ctitle("`:variable label `Y''") addtext(`addfe')
        local first 0
    }
}


****************************************************
* Tables 4-6: Heterogeneity (loop over Y * split var)
****************************************************
use "$DATA_PROCESSED/panel_main_stacked.dta", clear
do "label_variables.do"

* Build high/low volume split (only used for Table 6)
bys gvkey: egen vol_max = max(cond(treated == 1 & post == 1, total_volume, .))
summarize vol_max if treated == 1 & post == 1, detail
gen high_volume = vol_max > r(p50) & !missing(vol_max)
do "label_variables.do"

save "$DATA_TEMP/_het_panel.dta", replace

* Table 4: match_tier
use "$DATA_TEMP/_het_panel.dta", clear
local first 1
foreach Y of global Y_LIST {
    foreach sub in "" "if best_match_tier == 1 | treated == 0" "if best_match_tier == 2 | treated == 0" {
        local sample = cond("`sub'" == "", "Full Sample", ///
                       cond(strpos("`sub'", "== 1"), "Tier 1 (clean)", "Tier 2 (secondary)"))
        capture noisily reghdfe `Y' D $firm_controls `sub', ///
            absorb(gvkey#cohort_id qt#cohort_id) vce(cluster gvkey#cohort_id)
        if _rc == 0 {
            local cmd = cond(`first', "replace", "append")
            outreg2 using "$OUTPUT_TABLES/het_match_tier.xls", excel `cmd' dec(3) ///
                label nocon keep(D) ctitle("`:variable label `Y''", "`sample'") ///
                addtext(Firm Controls, Yes, Firm x Cohort FE, Yes, Quarter x Cohort FE, Yes)
            local first 0
        }
    }
}

* Table 5: mentioned_ceo
use "$DATA_TEMP/_het_panel.dta", clear
local first 1
foreach Y of global Y_LIST {
    foreach sub in "" "if mentioned_ceo_anymkt == 1 | treated == 0" "if mentioned_ceo_anymkt == 0 | treated == 0" {
        local sample = cond("`sub'" == "", "Full Sample", ///
                       cond(strpos("`sub'", "== 1"), "CEO Mentioned", "Company Only"))
        capture noisily reghdfe `Y' D $firm_controls `sub', ///
            absorb(gvkey#cohort_id qt#cohort_id) vce(cluster gvkey#cohort_id)
        if _rc == 0 {
            local cmd = cond(`first', "replace", "append")
            outreg2 using "$OUTPUT_TABLES/het_mentioned_ceo.xls", excel `cmd' dec(3) ///
                label nocon keep(D) ctitle("`:variable label `Y''", "`sample'") ///
                addtext(Firm Controls, Yes, Firm x Cohort FE, Yes, Quarter x Cohort FE, Yes)
            local first 0
        }
    }
}

* Table 6: high vs low volume
use "$DATA_TEMP/_het_panel.dta", clear
local first 1
foreach Y of global Y_LIST {
    foreach sub in "" "if high_volume == 1 | treated == 0" "if high_volume == 0 | treated == 0" {
        local sample = cond("`sub'" == "", "Full Sample", ///
                       cond(strpos("`sub'", "== 1"), "High Volume", "Low Volume"))
        capture noisily reghdfe `Y' D $firm_controls `sub', ///
            absorb(gvkey#cohort_id qt#cohort_id) vce(cluster gvkey#cohort_id)
        if _rc == 0 {
            local cmd = cond(`first', "replace", "append")
            outreg2 using "$OUTPUT_TABLES/het_volume.xls", excel `cmd' dec(3) ///
                label nocon keep(D) ctitle("`:variable label `Y''", "`sample'") ///
                addtext(Firm Controls, Yes, Firm x Cohort FE, Yes, Quarter x Cohort FE, Yes)
            local first 0
        }
    }
}

capture erase "$DATA_TEMP/_het_panel.dta"


****************************************************
* Table 7: TWFE switching-treatment (pulsed) robustness
****************************************************
use "$DATA_PROCESSED/panel_main.dta", clear
do "label_variables.do"

local first 1
foreach Y of global Y_LIST {
    capture noisily reghdfe `Y' D_active $firm_controls, ///
        absorb(gvkey qt) vce(cluster gvkey)
    if _rc == 0 {
        local cmd = cond(`first', "replace", "append")
        outreg2 using "$OUTPUT_TABLES/twfe_active_treatment.xls", excel `cmd' dec(3) ///
            label nocon keep(D_active) ctitle("`:variable label `Y''") ///
            addtext(Firm Controls, Yes, Firm FE, Yes, Quarter FE, Yes)
        local first 0
    }
}
