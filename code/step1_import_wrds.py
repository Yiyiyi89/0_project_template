# ****************************************************
# step1_import_wrds.py
# Input  : WRDS (comp.fundq, ibes.det_guidance,
#           wrdssec.items8k, ciq_transcripts,
#           execcomp.anncomp)
# Output : raw/wrds/compustat_fm_qt.parquet
#          raw/wrds/guidance_fm_qt.parquet
#          raw/wrds/eightk_fm_qt.parquet
#          raw/wrds/confcall_fm_qt.parquet
#          raw/wrds/ceo_fm_yr.parquet
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
#  1. Compustat Quarterly: firm-level controls
# ==============================================================
"""
Compustat Quarterly Fundamentals
"""
compustat = db.raw_sql("""
    SELECT gvkey, datadate, fyearq, fqtr, conm,
           atq, ltq, dlttq, dlcq, ceqq, cshoq, prccq,
           saleq, revtq, niq, ibq, oancfy, xrdq, xsgaq,
           dpq, capxy, ppentq, actq, lctq, cheq, invtq,
           txtq, piq, mkvaltq
    FROM comp.fundq
    WHERE indfmt = 'INDL'
      AND datafmt = 'STD'
      AND popsrc = 'D'
      AND consol = 'C'
      AND fyearq >= 2014
""")

print(f"Compustat quarterly raw: {compustat.shape[0]:,} rows")

# drop rows where atq is missing or non-positive — every ratio below uses it
compustat = compustat[compustat["atq"].notna() & (compustat["atq"] > 0)].reset_index(drop=True)

compustat["size"]      = np.log(compustat["atq"])
compustat["leverage"]  = (compustat["dlttq"].fillna(0) + compustat["dlcq"].fillna(0)) / compustat["atq"]
compustat["roa"]       = compustat["niq"] / compustat["atq"]

# mtb: only when ceqq > 0 (positive book equity)
ceqq_pos = compustat["ceqq"].where(compustat["ceqq"] > 0)
compustat["mtb"]       = (compustat["cshoq"] * compustat["prccq"]) / ceqq_pos

# sale_growth: only when prior-quarter saleq > 0 (avoid div-by-zero blow-ups)
compustat = compustat.sort_values(["gvkey", "fyearq", "fqtr"]).reset_index(drop=True)
prior_sale = compustat.groupby("gvkey")["saleq"].shift(1)
mask = ((prior_sale > 0) & compustat["saleq"].notna()).fillna(False).to_numpy()
compustat["sale_growth"] = np.where(
    mask,
    compustat["saleq"].to_numpy() / prior_sale.to_numpy() - 1.0,
    np.nan,
)

compustat["loss"]      = np.where(compustat["niq"].isna(), np.nan, (compustat["niq"] < 0).astype(float))
compustat["rd_int"]    = compustat["xrdq"].fillna(0) / compustat["atq"]
compustat["cfo"]       = compustat["oancfy"] / compustat["atq"]
compustat["tangibility"] = (compustat["ppentq"] / compustat["atq"]).clip(lower=0, upper=1)

compustat = compustat.drop_duplicates(subset=["gvkey", "fyearq", "fqtr"])
print(f"Compustat clean: {compustat.shape[0]:,} rows  ({compustat['gvkey'].nunique():,} firms)")

compustat.to_parquet(os.path.join(DATA_RAW_WRDS, "compustat_fm_qt.parquet"), index=False)
print("Saved: compustat_fm_qt.parquet")

# ==============================================================
#  2. IBES Guidance: voluntary disclosure (management forecasts)
# ==============================================================
"""
Management Earnings Guidance (det_guidance)
- frequency, precision, horizon of forecasts
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

    guidance["year"]    = pd.to_datetime(guidance["anndats"]).dt.year
    guidance["quarter"] = pd.to_datetime(guidance["anndats"]).dt.quarter

    guid_fq = guidance.groupby(["ticker", "year", "quarter"]).agg(
        n_forecasts     = ("anndats", "count"),
        n_point         = ("is_point", "sum"),
        n_range         = ("is_range", "sum"),
        avg_range_width = ("range_width", "mean"),
        avg_horizon     = ("horizon", "mean"),
    ).reset_index()

    guid_fq["frac_point"] = guid_fq["n_point"] / guid_fq["n_forecasts"]

    print(f"Guidance fm_qt: {guid_fq.shape[0]:,} rows  ({guid_fq['ticker'].nunique():,} firms)")

    guid_fq.to_parquet(os.path.join(DATA_RAW_WRDS, "guidance_fm_qt.parquet"), index=False)
    print("Saved: guidance_fm_qt.parquet")
except Exception as e:
    print(f"\n** IBES guidance skipped (no access): {e.__class__.__name__}")

# ==============================================================
#  3. 8-K Filings: voluntary disclosure (press releases, events)
# ==============================================================
"""
SEC 8-K Filings (wrdssec.items8k)
"""
eightk = db.raw_sql("""
    SELECT cik, coname, fdate, form, accession,
           nitem, item, nitemno
    FROM wrdssec.items8k
    WHERE fdate >= '2014-01-01'
""")

print(f"\n8-K raw: {eightk.shape[0]:,} rows")

eightk["year"]    = pd.to_datetime(eightk["fdate"]).dt.year
eightk["quarter"] = pd.to_datetime(eightk["fdate"]).dt.quarter

eightk_fq = eightk.groupby(["cik", "year", "quarter"]).agg(
    n_8k_filings = ("accession", "nunique"),
    n_8k_items   = ("item", "count"),
).reset_index()

print(f"8-K fm_qt: {eightk_fq.shape[0]:,} rows  ({eightk_fq['cik'].nunique():,} firms)")

eightk_fq.to_parquet(os.path.join(DATA_RAW_WRDS, "eightk_fm_qt.parquet"), index=False)
print("Saved: eightk_fm_qt.parquet")

# ==============================================================
#  4. Conference Calls: manager's public speaking
# ==============================================================
"""
Capital IQ Transcripts (earnings calls, investor days)
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

confcall["year"]    = pd.to_datetime(confcall["call_date"]).dt.year
confcall["quarter"] = pd.to_datetime(confcall["call_date"]).dt.quarter

# keydeveventtypename uses plural "Earnings Calls"; match case-insensitively
# to also catch any variant like "Earnings Call Transcript"
confcall["is_earnings"] = confcall["eventtype"].fillna("").str.contains(
    "earnings call", case=False, regex=False
).astype(int)

confcall_fq = confcall.groupby(["gvkey", "year", "quarter"]).agg(
    n_conf_calls    = ("transcriptid", "count"),
    n_earnings_call = ("is_earnings", "sum"),
).reset_index()

confcall_fq = confcall_fq.dropna(subset=["gvkey"])
print(f"Conf call fm_qt: {confcall_fq.shape[0]:,} rows  ({confcall_fq['gvkey'].nunique():,} firms)")

confcall_fq.to_parquet(os.path.join(DATA_RAW_WRDS, "confcall_fm_qt.parquet"), index=False)
print("Saved: confcall_fm_qt.parquet")

# ==============================================================
#  5. ExecuComp: CEO names (annual only)
# ==============================================================
"""
ExecuComp Annual Compensation
- CEO identification via ceoann flag
- annual granularity (no quarterly in ExecuComp)
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
year_end = pd.to_datetime(ceo["year"].astype(int).astype(str) + "-12-31", format="%Y-%m-%d")
ceo["tenure_years"] = (year_end - ceo["becameceo"]).dt.days / 365.25
# year < becameceo means the row predates this person's CEO term — null it out
ceo.loc[ceo["tenure_years"] < 0, "tenure_years"] = np.nan

ceo = ceo.drop_duplicates(subset=["gvkey", "year"])
print(f"CEO fm_yr: {ceo.shape[0]:,} rows  ({ceo['gvkey'].nunique():,} firms)")

ceo.to_parquet(os.path.join(DATA_RAW_WRDS, "ceo_fm_yr.parquet"), index=False)
print("Saved: ceo_fm_yr.parquet")

# ==============================================================
db.close()
print(f"\nDone — all saved to {DATA_RAW_WRDS}")
