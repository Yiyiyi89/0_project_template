* =============================================================
* Variable Labels — sourced from variables.yaml
* Run after loading data to apply consistent labels
* =============================================================

* --- Treatment ---
capture label var D                         "Post-COE Convergence"
capture label var post_isa_conv              "Post-ISA Convergence"

* --- Dependent: Accruals Quality ---
capture label var aq_dd                     "Accruals Quality (DD)"
capture label var aq_bs                     "Accruals Quality (BS)"
capture label var aq_mdd                    "Accruals Quality (Modified DD)"
capture label var abs_dd_resid              "Abs. DD Residual"
capture label var absda                     "Abs. Discr. Accruals"
capture label var absda_adjmodjones         "Abs. DA (Adj. Mod. Jones)"
capture label var absda_jones               "Abs. DA (Jones)"

* --- Dependent: Real Earnings Management ---
capture label var ab_cfo                    "Abnormal CFO"
capture label var ab_prod                   "Abnormal Production Costs"
capture label var ab_disc_exp               "Abnormal Discr. Expenses"
capture label var rem_combined              "Combined REM"

* --- Dependent: EM Composites ---
capture label var em1_firm                  "EM Composite 1"
capture label var em3_firm                  "EM Composite 3"

* --- Dependent: Loss Avoidance ---
capture label var small_loss                "Small Loss"
capture label var small_profit              "Small Profit"

* --- Dependent: Audit ---
capture label var audit_fees_ln             "Log Audit Fees"
capture label var ab_audit_fees             "Abnormal Audit Fees"
capture label var auditor_change            "Auditor Change"
capture label var audit_opinion             "Audit Opinion"
capture label var tenure                    "Auditor Tenure"
capture label var aggressiveness            "Reporting Aggressiveness"
capture label var signed_da                 "Signed Discr. Accruals"

* --- Firm Controls ---
capture label var size_lag1                 "Firm Size (t-1)"
capture label var leverage_lag1             "Leverage (t-1)"
capture label var sales_growth_lag1         "Sales Growth (t-1)"
capture label var ppe_growth_lag1           "PPE Growth (t-1)"
capture label var roa_lag1                  "ROA (t-1)"
capture label var loss_lag1                 "Loss Indicator (t-1)"
capture label var ifrs_lag1                 "IFRS Adoption (t-1)"

* --- Country Controls ---
capture label var wgi_avg_cy_yr_lag1         "Governance Index (t-1)"
capture label var ln_gdp_usd_cy_yr_lag1      "Log GDP p.c. (t-1)"
capture label var ln_cpi_cy_yr_lag1          "Log CPI (t-1)"
capture label var ln_fx_rate_cy_yr_lag1      "Log FX Rate (t-1)"
capture label var ln_listed_firms_cy_yr_lag1 "Log Listed Firms (t-1)"
capture label var mktcap_gdp_cy_yr_lag1      "Market Cap/GDP (t-1)"

* --- Splits ---
capture label var big4                      "Big 4 Auditor"
