# ****************************************************
# step1_import_wrds.py
# Input  : WRDS (comp.funda, ibes.det_guidance,
#           wrdssec.wrds_sec_8k, tr.tr_transcript,
#           execcomp.anncomp)
# Output : temp/compustat_firm_year.parquet
#          temp/guidance_firm_year.parquet
#          temp/eightk_firm_year.parquet
#          temp/confcall_firm_year.parquet
#          temp/ceo_firm_year.parquet
# ****************************************************

import os
import pandas as pd
import numpy as np
import wrds

from config import DATA_TEMP

db = wrds.Connection()

# ==============================================================
#  1. Compustat: firm-level controls
# ==============================================================
"""
Compustat Annual Fundamentals
"""
compustat = db.raw_sql("""
    SELECT gvkey, datadate, fyear, conm,
           at, lt, dltt, dlc, ceq, csho, prcc_f,
           sale, revt, ni, ib, oancf, xrd, xad, xsga,
           dp, capx, ppent, act, lct, che, invt,
           txt, pi, mkvalt
    FROM comp.funda
    WHERE indfmt = 'INDL'
      AND datafmt = 'STD'
      AND popsrc = 'D'
      AND consol = 'C'
      AND fyear >= 2014
""")

print(f"Compustat raw: {compustat.shape[0]:,} rows")

# construct controls
compustat["size"]      = np.log(compustat["at"].clip(lower=1))
compustat["leverage"]  = (compustat["dltt"] + compustat["dlc"]) / compustat["at"]
compustat["roa"]       = compustat["ni"] / compustat["at"]
compustat["mtb"]       = (compustat["csho"] * compustat["prcc_f"]) / compustat["ceq"]
compustat["sale_growth"] = compustat.sort_values(["gvkey", "fyear"]).groupby("gvkey")["sale"].pct_change()
compustat["loss"]      = (compustat["ni"] < 0).astype(int)
compustat["rd_int"]    = compustat["xrd"].fillna(0) / compustat["at"]
compustat["ad_int"]    = compustat["xad"].fillna(0) / compustat["at"]
compustat["capx_int"]  = compustat["capx"].fillna(0) / compustat["at"]
compustat["cfo"]       = compustat["oancf"] / compustat["at"]
compustat["tangibility"] = compustat["ppent"] / compustat["at"]

compustat = compustat.drop_duplicates(subset=["gvkey", "fyear"])
print(f"Compustat clean: {compustat.shape[0]:,} rows  ({compustat['gvkey'].nunique():,} firms)")

compustat.to_parquet(os.path.join(DATA_TEMP, "compustat_firm_year.parquet"), index=False)
print("Saved: compustat_firm_year.parquet")

# ==============================================================
#  2. IBES Guidance: voluntary disclosure (management forecasts)
# ==============================================================
"""
Management Earnings Guidance (det_guidance)
- frequency, precision, horizon of forecasts
"""
guidance = db.raw_sql("""
    SELECT ticker, oftic, cname, analession AS gvkey_ibes,
           anndats, anntims, periodtype, measure,
           val1, val2, val3, val4,
           pdicity, fiscalper, fiscalyear,
           units, curr_act, usfirm
    FROM ibes.det_guidance
    WHERE anndats >= '2014-01-01'
      AND usfirm = 1
""")

print(f"\nIBES guidance raw: {guidance.shape[0]:,} rows")

# forecast precision: point (val1=val2), range (val1!=val2), qualitative (missing)
guidance["is_point"]    = (guidance["val1"] == guidance["val2"]).astype(int)
guidance["is_range"]    = ((guidance["val1"].notna()) & (guidance["val2"].notna()) & (guidance["val1"] != guidance["val2"])).astype(int)
guidance["range_width"] = (guidance["val2"] - guidance["val1"]).abs()
guidance["horizon"]     = (pd.to_datetime(guidance["fiscalyear"].astype(str) + "-12-31", errors="coerce") - pd.to_datetime(guidance["anndats"])).dt.days

# aggregate to firm-year
guidance["year"] = pd.to_datetime(guidance["anndats"]).dt.year
guid_fy = guidance.groupby(["oftic", "year"]).agg(
    n_forecasts     = ("anndats", "count"),
    n_point         = ("is_point", "sum"),
    n_range         = ("is_range", "sum"),
    avg_range_width = ("range_width", "mean"),
    avg_horizon     = ("horizon", "mean"),
).reset_index()

guid_fy["frac_point"] = guid_fy["n_point"] / guid_fy["n_forecasts"]

print(f"Guidance firm-year: {guid_fy.shape[0]:,} rows  ({guid_fy['oftic'].nunique():,} firms)")

guid_fy.to_parquet(os.path.join(DATA_TEMP, "guidance_firm_year.parquet"), index=False)
print("Saved: guidance_firm_year.parquet")

# ==============================================================
#  3. 8-K Filings: voluntary disclosure (press releases, events)
# ==============================================================
"""
SEC 8-K Filings
- item types indicate disclosure type
"""
eightk = db.raw_sql("""
    SELECT cik, company_name, filing_date, form_type,
           item_list, file_date, accession_number
    FROM wrdssec.wrds_sec_8k
    WHERE filing_date >= '2014-01-01'
""")

print(f"\n8-K raw: {eightk.shape[0]:,} rows")

eightk["year"] = pd.to_datetime(eightk["filing_date"]).dt.year

eightk_fy = eightk.groupby(["cik", "year"]).agg(
    n_8k_filings = ("accession_number", "count"),
).reset_index()

print(f"8-K firm-year: {eightk_fy.shape[0]:,} rows  ({eightk_fy['cik'].nunique():,} firms)")

eightk_fy.to_parquet(os.path.join(DATA_TEMP, "eightk_firm_year.parquet"), index=False)
print("Saved: eightk_firm_year.parquet")

# ==============================================================
#  4. Conference Calls: manager's public speaking
# ==============================================================
"""
Capital IQ Transcripts (earnings calls, investor days)
- proxy for manager's public speaking
"""
confcall = db.raw_sql("""
    SELECT companyid, companyname, gvkey,
           mostimportantdateutc AS call_date,
           transcriptid, headline, eventtype
    FROM tr.tr_transcript
    WHERE mostimportantdateutc >= '2014-01-01'
""")

print(f"\nConf calls raw: {confcall.shape[0]:,} rows")

confcall["year"] = pd.to_datetime(confcall["call_date"]).dt.year

confcall_fy = confcall.groupby(["gvkey", "year"]).agg(
    n_conf_calls   = ("transcriptid", "count"),
    n_earnings_call = ("eventtype", lambda x: (x == "Earnings Call").sum()),
    n_investor_day  = ("eventtype", lambda x: (x == "Investor Day").sum()),
).reset_index()

print(f"Conf call firm-year: {confcall_fy.shape[0]:,} rows  ({confcall_fy['gvkey'].nunique():,} firms)")

confcall_fy.to_parquet(os.path.join(DATA_TEMP, "confcall_firm_year.parquet"), index=False)
print("Saved: confcall_firm_year.parquet")

# ==============================================================
#  5. ExecuComp: CEO names
# ==============================================================
"""
ExecuComp Annual Compensation
- CEO identification via ceoann flag
"""
ceo = db.raw_sql("""
    SELECT gvkey, year, exec_fullname, coname,
           ceoann, titleann, gender, age,
           becameceo, joined_co, leftofc,
           salary, bonus, tdc1, tdc2
    FROM execcomp.anncomp
    WHERE ceoann = 'CEO'
      AND year >= 2014
""")

print(f"\nExecuComp CEO raw: {ceo.shape[0]:,} rows")

ceo["becameceo"] = pd.to_datetime(ceo["becameceo"], errors="coerce")
ceo["leftofc"]   = pd.to_datetime(ceo["leftofc"], errors="coerce")
ceo["tenure_years"] = (pd.to_datetime(ceo["year"].astype(str) + "-12-31") - ceo["becameceo"]).dt.days / 365.25

ceo = ceo.drop_duplicates(subset=["gvkey", "year"])
print(f"CEO firm-year: {ceo.shape[0]:,} rows  ({ceo['gvkey'].nunique():,} firms)")

ceo.to_parquet(os.path.join(DATA_TEMP, "ceo_firm_year.parquet"), index=False)
print("Saved: ceo_firm_year.parquet")

# ==============================================================
db.close()
print("\nDone — all saved to DATA_TEMP")
