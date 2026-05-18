* =============================================================
* label_variables.do
* Variable labels for panel_fm_qt_mkt.dta
* Apply after loading the firm-quarter-market panel
*
* Source annotations:
*   POLY     = raw Polymarket (data/raw/markets.parquet)
*   LLM      = LLM classification (step2_LLM_classification.py)
*   LINK     = entity linkage (step2_5_link_entities.py)
*   COMPU    = WRDS Compustat (raw/wrds/compustat_fm_qt.parquet)
*   CONFCALL = WRDS Conference Calls (raw/wrds/confcall_fm_qt.parquet)
*   EXEC     = WRDS ExecuComp (raw/wrds/ceo_fm_yr.parquet)
*   DERIVED  = constructed in step4_build_up_panel.py
*   DERIVED4 = constructed in step4_panels.do (firm-quarter collapse, treatment, lags)
* =============================================================

* ---------------- Identifiers ----------------
capture label var gvkey                "Compustat firm identifier (gvkey)"                       // COMPU
capture label var year                 "Calendar year"                                            // COMPU (fyearq) / DERIVED
capture label var quarter              "Calendar quarter (1-4)"                                   // COMPU (fqtr) / DERIVED
capture label var yearqtr              "Year-quarter string (e.g. 2023Q2)"                        // DERIVED
capture label var conm                 "Company name (Compustat)"                                 // COMPU
capture label var i_treated_firm       "Firm linked to at least one Polymarket market (0/1)"      // DERIVED

* ---------------- Market identifiers ----------------
capture label var market_id            "Polymarket market id"                                     // POLY
capture label var slug                 "Polymarket market slug (URL handle)"                      // POLY
capture label var question             "Market question text"                                     // POLY
capture label var description          "Market description text"                                  // POLY

* ---------------- Entity-link info ----------------
capture label var match_tier           "Match quality tier (1=best, 2=secondary)"                 // LINK
capture label var mentioned_ceo        "Market mentions firm's CEO by name (0/1)"                 // LINK
capture label var i_mention            "Sources matched: 1=CEO or company only, 2=both"           // LINK
capture label var person_name          "Person name from market NER (matched to CEO)"             // LINK
capture label var company_name         "Company name from market NER (matched to Compustat)"      // LINK
capture label var ceo_name             "CEO full name from ExecuComp (matched)"                   // LINK
capture label var coname               "Firm name from match source (ExecuComp / Compustat)"      // LINK

* ---------------- Market timing & status ----------------
capture label var created_at           "Market creation timestamp (UTC)"                          // POLY
capture label var closed_time          "Market close timestamp (UTC); null filled with 2026-01-01" // POLY (cleaned)
capture label var end_date             "Scheduled end date (UTC)"                                 // POLY
capture label var start_date           "Scheduled start date (UTC)"                               // POLY
capture label var market_duration_days "Market lifetime: closed_time - created_at (days)"         // DERIVED
capture label var i_resolved           "Market resolved before 2026-01-01 cutoff (0/1)"           // DERIVED
capture label var closed               "Market is closed (Polymarket flag)"                       // POLY
capture label var active               "Market is active (Polymarket flag)"                       // POLY
capture label var archived             "Market is archived (Polymarket flag)"                     // POLY
capture label var restricted           "Market is restricted (Polymarket flag)"                   // POLY
capture label var approved             "Market is approved (Polymarket flag)"                     // POLY
capture label var new                  "Market is new (Polymarket flag)"                          // POLY
capture label var featured             "Market is featured (Polymarket flag)"                     // POLY
capture label var neg_risk             "Market is part of a negative-risk set (Polymarket flag)"  // POLY

* ---------------- LLM category / NER entities ----------------
capture label var category_llm         "LLM-assigned market category"                             // LLM
capture label var subcategory_llm      "LLM-assigned market subcategory"                          // LLM
capture label var ner_persons          "Named entities: persons (JSON list)"                      // LLM
capture label var ner_companies        "Named entities: companies (JSON list)"                    // LLM
capture label var ner_organizations    "Named entities: organizations (JSON list)"                // LLM

* ---------------- Market volume & liquidity ----------------
capture label var volume_num           "Cumulative trading volume (USD)"                          // POLY
capture label var ln_volume            "Log(1 + volume_num)"                                      // DERIVED
capture label var volume_24hr          "Trading volume last 24 hours (USD)"                       // POLY
capture label var volume_1wk           "Trading volume last 1 week (USD)"                         // POLY
capture label var volume_1mo           "Trading volume last 1 month (USD)"                        // POLY
capture label var volume_1yr           "Trading volume last 1 year (USD)"                         // POLY
capture label var liquidity_num        "Current liquidity (USD)"                                  // POLY
capture label var competitive          "Polymarket competitiveness score"                         // POLY
capture label var spread               "Bid-ask spread"                                           // POLY

* ---------------- Market price & outcomes ----------------
capture label var last_trade_price     "Last traded price (YES outcome)"                          // POLY
capture label var best_bid             "Best bid price"                                           // POLY
capture label var best_ask             "Best ask price"                                           // POLY
capture label var one_day_price_change "Price change last 1 day"                                  // POLY
capture label var one_week_price_change  "Price change last 1 week"                               // POLY
capture label var one_month_price_change "Price change last 1 month"                              // POLY
capture label var one_year_price_change  "Price change last 1 year"                               // POLY
capture label var outcomes             "Outcome labels (JSON list)"                               // POLY
capture label var outcome_prices       "Outcome prices (JSON list)"                               // POLY
capture label var resolution_source    "URL of resolution source"                                 // POLY
capture label var resolved_by          "Address that resolved the market"                         // POLY

* ---------------- Firm-quarter financials (Compustat) ----------------
capture label var size                 "Firm size = ln(atq)"                                      // COMPU
capture label var leverage             "Leverage = (dlcq + dlttq) / atq"                          // COMPU
capture label var roa                  "Return on assets = niq / atq"                             // COMPU
capture label var mtb                  "Market-to-book = mkvaltq / ceqq"                          // COMPU
capture label var sale_growth          "Quarterly sales growth"                                   // COMPU
capture label var loss                 "Loss indicator: niq < 0 (0/1)"                            // COMPU
capture label var rd_int               "R&D intensity = xrdq / saleq"                             // COMPU
capture label var cfo                  "Cash flow from operations / atq"                          // COMPU
capture label var tangibility          "Tangibility = ppentq / atq"                               // COMPU
capture label var atq                  "Total assets (Compustat quarterly)"                       // COMPU
capture label var saleq                "Sales / revenue (Compustat quarterly)"                    // COMPU
capture label var niq                  "Net income (Compustat quarterly)"                         // COMPU
capture label var mkvaltq              "Market value of equity (Compustat quarterly)"             // COMPU

* ---------------- Firm-quarter voluntary disclosure ----------------
capture label var n_conf_calls         "Number of conference calls in quarter"                    // CONFCALL
capture label var n_earnings_call      "Number of earnings calls in quarter"                      // CONFCALL

* ---------------- CEO characteristics (ExecuComp, annual) ----------------
capture label var ceo_name_wrds        "CEO full name (ExecuComp exec_fullname)"                  // EXEC
capture label var gender               "CEO gender (M/F)"                                         // EXEC
capture label var age                  "CEO age (years)"                                          // EXEC
capture label var tenure_years         "CEO tenure (years)"                                       // EXEC
capture label var salary               "CEO salary (USD thousands)"                               // EXEC
capture label var bonus                "CEO bonus (USD thousands)"                                // EXEC
capture label var tdc1                 "CEO total direct compensation (TDC1, USD thousands)"      // EXEC

* =============================================================
* step4_panels.do constructions (firm-quarter collapse + DiD setup)
* =============================================================

* ---------------- Time & treatment timing ----------------
capture label var qt                   "Calendar quarter (integer, year*4+quarter-1)"             // DERIVED4
capture label var qt_first_market      "Quarter of first market mention (treatment timing)"      // DERIVED4
capture label var treated_firm         "Firm ever covered by a Polymarket market (0/1)"           // DERIVED4

* ---------------- Treatment indicators ----------------
capture label var D_post               "Post First-Mention (absorbing treatment)"                // DERIVED4
capture label var D_active             "Active Market in firm-quarter (TWFE switching)"          // DERIVED4
capture label var i_has_market         "Any market active in firm-quarter (0/1)"                  // DERIVED4

* ---------------- Aggregated market activity (firm-quarter) ----------------
capture label var n_markets            "# markets active in firm-quarter"                         // DERIVED4
capture label var total_volume         "Sum of volume across active markets (USD)"                // DERIVED4
capture label var mean_volume          "Mean volume per active market (USD)"                      // DERIVED4
capture label var best_match_tier      "Best (min) match tier across firm's markets that quarter" // DERIVED4
capture label var mentioned_ceo_anymkt "Any market this quarter mentions the CEO (0/1)"           // DERIVED4
capture label var i_resolved_anymkt    "Any market this quarter resolved by 2026-01-01 (0/1)"     // DERIVED4

* ---------------- Outcomes (voluntary disclosure) ----------------
capture label var ln_conf_calls        "Log(1 + # conf calls)"                                    // DERIVED4
capture label var ln_earnings_call     "Log(1 + # earnings calls)"                                // DERIVED4
capture label var i_has_call           "Any conference call this quarter (0/1)"                   // DERIVED4
capture label var frac_earnings        "Share of conf calls that are earnings calls"              // DERIVED4

* ---------------- Lagged controls (t-1) ----------------
capture label var size_lag1            "Firm Size (t-1)"                                          // DERIVED4
capture label var leverage_lag1        "Leverage (t-1)"                                           // DERIVED4
capture label var roa_lag1             "ROA (t-1)"                                                // DERIVED4
capture label var mtb_lag1             "Market-to-Book (t-1)"                                     // DERIVED4
capture label var sale_growth_lag1     "Sales Growth (t-1)"                                       // DERIVED4
capture label var loss_lag1            "Loss Indicator (t-1)"                                     // DERIVED4

* =============================================================
* Stacked-DiD constructions (panel_main_stacked)
* =============================================================
capture label var cohort               "Cohort = qt_first_market (calendar quarter)"              // DERIVED4
capture label var cohort_id            "Cohort numeric id"                                        // DERIVED4
capture label var treated              "Treated firm within this sub-experiment"                  // DERIVED4
capture label var rt                   "Event time (qt - cohort)"                                 // DERIVED4
capture label var post                 "Post-event indicator (rt >= 0)"                           // DERIVED4
capture label var D                    "Post Market Mention (stacked DiD treatment)"              // DERIVED4
capture label var time_to_treat        "Event time for treated rows (missing for controls)"       // DERIVED4

* Heterogeneity splits (built in step5_tables.do)
capture label var vol_max              "Max market volume firm experienced (treated only)"        // DERIVED4
capture label var high_volume          "Firm's max market volume above median (0/1)"              // DERIVED4
