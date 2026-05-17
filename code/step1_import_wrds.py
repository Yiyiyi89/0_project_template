# ****************************************************
# step1_import_wrds.py
# Input  : WRDS (comp.funda, ibes.det_guidance,
#           wrdssec.items8k, ciq_transcripts,
#           execcomp.anncomp)
# Output : raw/wrds/compustat_firm_year.parquet
#          raw/wrds/guidance_firm_year.parquet
#          raw/wrds/eightk_firm_year.parquet
#          raw/wrds/confcall_firm_year.parquet
#          raw/wrds/ceo_firm_year.parquet
# ****************************************************

import os
import pandas as pd
import numpy as np
import wrds

from config import DATA_RAW_WRDS

os.makedirs(DATA_RAW_WRDS, exist_ok=True)

WRDS_USER = os.environ["WRDS_USERNAME"]
WRDS_PASS = os.environ["WRDS_PASSWORD"]

db = wrds.Connection(wrds_username=WRDS_USER, wrds_password=WRDS_PASS)

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

compustat["size"]      = np.log(compustat["at"].clip(lower=1))
compustat["leverage"]  = (compustat["dltt"] + compustat["dlc"]) / compustat["at"]
compustat["roa"]       = compustat["ni"] / compustat["at"]
compustat["mtb"]       = (compustat["csho"] * compustat["prcc_f"]) / compustat["ceq"]
compustat["sale_growth"] = compustat.sort_values(["gvkey", "fyear"]).groupby("gvkey")["sale"].pct_change(fill_method=None)
compustat["loss"]      = np.where(compustat["ni"].isna(), np.nan, (compustat["ni"] < 0).astype(float))
compustat["rd_int"]    = compustat["xrd"].fillna(0) / compustat["at"]
compustat["ad_int"]    = compustat["xad"].fillna(0) / compustat["at"]
compustat["capx_int"]  = compustat["capx"].fillna(0) / compustat["at"]
compustat["cfo"]       = compustat["oancf"] / compustat["at"]
compustat["tangibility"] = compustat["ppent"] / compustat["at"]

compustat = compustat.drop_duplicates(subset=["gvkey", "fyear"])
print(f"Compustat clean: {compustat.shape[0]:,} rows  ({compustat['gvkey'].nunique():,} firms)")

compustat.to_parquet(os.path.join(DATA_RAW_WRDS, "compustat_firm_year.parquet"), index=False)
print("Saved: compustat_firm_year.parquet")

# ==============================================================
#  2. IBES Guidance: voluntary disclosure (management forecasts)
# ==============================================================
"""
Management Earnings Guidance (det_guidance)
- frequency, precision, horizon of forecasts
- uses tr_ibes schema (Thomson Reuters IBES)
"""
try:
    guidance = db.raw_sql("""
        SELECT ticker, anndats, anntims, pdicity, measure,
               val_1, val_2, range_desc, guidance_code,
               prd_yr, prd_mon, units, usfirm
        FROM tr_ibes.det_guidance
        WHERE anndats >= '2014-01-01'
          AND usfirm = 1
    """)

    print(f"\nIBES guidance raw: {guidance.shape[0]:,} rows")

    guidance["is_point"]    = (guidance["val_1"] == guidance["val_2"]).astype(int)
    guidance["is_range"]    = ((guidance["val_1"].notna()) & (guidance["val_2"].notna()) & (guidance["val_1"] != guidance["val_2"])).astype(int)
    guidance["range_width"] = (guidance["val_2"] - guidance["val_1"]).abs()
    guidance["horizon"]     = (pd.to_datetime(guidance["prd_yr"].astype(int).astype(str) + "-12-31", errors="coerce") - pd.to_datetime(guidance["anndats"])).dt.days

    guidance["year"] = pd.to_datetime(guidance["anndats"]).dt.year
    guid_fy = guidance.groupby(["ticker", "year"]).agg(
        n_forecasts     = ("anndats", "count"),
        n_point         = ("is_point", "sum"),
        n_range         = ("is_range", "sum"),
        avg_range_width = ("range_width", "mean"),
        avg_horizon     = ("horizon", "mean"),
    ).reset_index()

    guid_fy["frac_point"] = guid_fy["n_point"] / guid_fy["n_forecasts"]

    print(f"Guidance firm-year: {guid_fy.shape[0]:,} rows  ({guid_fy['ticker'].nunique():,} firms)")

    guid_fy.to_parquet(os.path.join(DATA_RAW_WRDS, "guidance_firm_year.parquet"), index=False)
    print("Saved: guidance_firm_year.parquet")
except Exception as e:
    print(f"\n** IBES guidance skipped (no access): {e.__class__.__name__}")

# ==============================================================
#  3. 8-K Filings: voluntary disclosure (press releases, events)
# ==============================================================
"""
SEC 8-K Filings (wrdssec.items8k)
- item types indicate disclosure type
"""
eightk = db.raw_sql("""
    SELECT cik, coname, fdate, form, accession,
           nitem, item, nitemno
    FROM wrdssec.items8k
    WHERE fdate >= '2014-01-01'
""")

print(f"\n8-K raw: {eightk.shape[0]:,} rows")

eightk["year"] = pd.to_datetime(eightk["fdate"]).dt.year

eightk_fy = eightk.groupby(["cik", "year"]).agg(
    n_8k_filings = ("accession", "nunique"),
    n_8k_items   = ("item", "count"),
).reset_index()

print(f"8-K firm-year: {eightk_fy.shape[0]:,} rows  ({eightk_fy['cik'].nunique():,} firms)")

eightk_fy.to_parquet(os.path.join(DATA_RAW_WRDS, "eightk_firm_year.parquet"), index=False)
print("Saved: eightk_firm_year.parquet")

# ==============================================================
#  4. Conference Calls: manager's public speaking
# ==============================================================
"""
Capital IQ Transcripts (earnings calls, investor days)
- use ciq_transcripts.wrds_transcript_detail
- link to gvkey via ciq_common.wrds_gvkey
"""
confcall = db.raw_sql("""
    SELECT t.companyid, t.companyname, t.transcriptid,
           t.headline, t.mostimportantdateutc AS call_date,
           t.keydeveventtypename AS eventtype,
           g.gvkey
    FROM ciq_transcripts.wrds_transcript_detail t
    LEFT JOIN ciq_common.wrds_gvkey g
      ON t.companyid = g.companyid
    WHERE t.mostimportantdateutc >= '2014-01-01'
""")

print(f"\nConf calls raw: {confcall.shape[0]:,} rows")

confcall["year"] = pd.to_datetime(confcall["call_date"]).dt.year

confcall_fy = confcall.groupby(["gvkey", "year"]).agg(
    n_conf_calls    = ("transcriptid", "count"),
    n_earnings_call = ("eventtype", lambda x: (x == "Earnings Call").sum()),
).reset_index()

confcall_fy = confcall_fy.dropna(subset=["gvkey"])
print(f"Conf call firm-year: {confcall_fy.shape[0]:,} rows  ({confcall_fy['gvkey'].nunique():,} firms)")

confcall_fy.to_parquet(os.path.join(DATA_RAW_WRDS, "confcall_firm_year.parquet"), index=False)
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
ceo["tenure_years"] = (pd.to_datetime(ceo["year"].astype(int).astype(str) + "-12-31", format="%Y-%m-%d") - ceo["becameceo"]).dt.days / 365.25

ceo = ceo.drop_duplicates(subset=["gvkey", "year"])
print(f"CEO firm-year: {ceo.shape[0]:,} rows  ({ceo['gvkey'].nunique():,} firms)")

ceo.to_parquet(os.path.join(DATA_RAW_WRDS, "ceo_firm_year.parquet"), index=False)
print("Saved: ceo_firm_year.parquet")

# ==============================================================
db.close()
print(f"\nDone — all saved to {DATA_RAW_WRDS}")
