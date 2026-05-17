# ****************************************************
# step2_5_link_entities.py
# Input  : temp/markets_categories_entities_selected.parquet
#           raw/wrds/ceo_fm_yr.parquet
#           raw/wrds/compustat_fm_qt.parquet
# Output : temp/market_names.parquet
#           temp/key_market_ceo.parquet
#           temp/key_market_company.parquet
#           temp/key_market_company_full.parquet
# ****************************************************

import os
import json
import re
import pandas as pd
import numpy as np
from splink import Linker, DuckDBAPI, SettingsCreator, block_on
from splink import comparison_library as cl

from config import DATA_TEMP, DATA_RAW_WRDS

os.makedirs(DATA_TEMP, exist_ok=True)

SUFFIX_RE = re.compile(
    r"\b(INC|INCORPORATED|CORP|CORPORATION|LLC|LTD|LIMITED|CO|"
    r"COMPANY|PLC|GROUP|HOLDINGS|HOLD|LP|NV|SA|AG|SE|"
    r"TECHNOLOGIES|TECHNOLOGY|SYSTEMS|INTL|INTERNATIONAL)\b",
    re.IGNORECASE
)

def normalize_name(s):
    s = s.upper().strip()
    s = re.sub(r"[.,']", "", s)
    s = SUFFIX_RE.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

# ==============================================================
#  Step A: Extract unique names → temp/market_names.parquet
# ==============================================================
"""
Parse NER JSON lists, explode to one row per (market_id, name, type)
"""
cats = pd.read_parquet(os.path.join(DATA_TEMP, "markets_categories_entities_selected.parquet"))
print(f"Selected markets: {cats.shape[0]:,}")

rows = []
for _, r in cats.iterrows():
    mid = r["id"]
    for col, ntype in [("ner_persons", "person"), ("ner_companies", "company")]:
        raw = r[col]
        if pd.isna(raw):
            continue
        try:
            names = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        for name in names:
            if name and len(name.strip()) > 1:
                rows.append({"market_id": mid, "name": name.strip(), "type": ntype})

market_names = pd.DataFrame(rows)
print(f"Exploded names: {market_names.shape[0]:,} rows")
print(f"  persons:   {(market_names['type']=='person').sum():,}")
print(f"  companies: {(market_names['type']=='company').sum():,}")
print(f"  unique persons:   {market_names.loc[market_names['type']=='person','name'].nunique():,}")
print(f"  unique companies: {market_names.loc[market_names['type']=='company','name'].nunique():,}")

market_names.to_parquet(os.path.join(DATA_TEMP, "market_names.parquet"), index=False)
print("Saved: market_names.parquet")

# ==============================================================
#  Step B: Build WRDS reference tables (deduplicated)
# ==============================================================
"""
CEO reference: latest year per gvkey → unique (exec_fullname, gvkey, coname)
Company reference: unique (gvkey, conm) from compustat
"""
ceo_raw = pd.read_parquet(os.path.join(DATA_RAW_WRDS, "ceo_fm_yr.parquet"))
ceo_raw["year"] = ceo_raw["year"].astype(int)
ceo_ref = (ceo_raw.sort_values("year", ascending=False)
           .drop_duplicates(subset=["gvkey"], keep="first")
           [["gvkey", "exec_fullname", "coname"]]
           .reset_index(drop=True))
print(f"\nCEO reference: {ceo_ref.shape[0]:,} unique (gvkey, ceo_name)")

comp_raw = pd.read_parquet(os.path.join(DATA_RAW_WRDS, "compustat_fm_qt.parquet"),
                           columns=["gvkey", "conm"])
comp_ref = comp_raw.drop_duplicates(subset=["gvkey"]).reset_index(drop=True)
print(f"Company reference: {comp_ref.shape[0]:,} unique (gvkey, conm)")

# ==============================================================
#  Step C: Splink fuzzy merge — person names → CEOs
# ==============================================================
"""
Left:  unique person names from polymarket
Right: unique CEO names from ExecuComp
Match on normalized name via Jaro-Winkler
"""
print("\n" + "="*60)
print("  Step C: Person → CEO matching (splink)")
print("="*60)

persons_unique = (market_names[market_names["type"] == "person"][["name"]]
                  .drop_duplicates().reset_index(drop=True))
persons_unique["unique_id"] = range(len(persons_unique))
persons_unique["name_clean"] = persons_unique["name"].apply(normalize_name)
persons_unique = persons_unique[persons_unique["name_clean"].str.len() > 1].reset_index(drop=True)

ceo_unique = ceo_ref[["exec_fullname", "gvkey", "coname"]].copy()
ceo_unique["unique_id"] = range(len(ceo_unique))
ceo_unique["name_clean"] = ceo_unique["exec_fullname"].apply(normalize_name)
ceo_unique = ceo_unique[ceo_unique["name_clean"].str.len() > 1].reset_index(drop=True)

print(f"  Left (persons): {len(persons_unique):,} unique names")
print(f"  Right (CEOs):   {len(ceo_unique):,} unique names")

df_l_ceo = persons_unique[["unique_id", "name_clean"]].rename(columns={"name_clean": "name_norm"})
df_r_ceo = ceo_unique[["unique_id", "name_clean"]].rename(columns={"name_clean": "name_norm"})

settings_ceo = SettingsCreator(
    link_type="link_only",
    comparisons=[cl.JaroWinklerAtThresholds("name_norm", [0.92, 0.85])],
    blocking_rules_to_generate_predictions=[
        "substr(l.name_norm,1,1) = substr(r.name_norm,1,1)"
    ],
    probability_two_random_records_match=0.05,
)

linker_ceo = Linker([df_l_ceo, df_r_ceo], settings_ceo, DuckDBAPI(),
                    input_table_aliases=["polymarket_persons", "wrds_ceos"])
linker_ceo.training.estimate_u_using_random_sampling(max_pairs=1e6)

preds_ceo = linker_ceo.inference.predict(threshold_match_probability=0.1)
df_preds_ceo = preds_ceo.as_pandas_dataframe()
print(f"  Raw matches: {df_preds_ceo.shape[0]:,}")

if len(df_preds_ceo) > 0:
    # keep best match per left record
    df_preds_ceo = df_preds_ceo.sort_values("match_probability", ascending=False)
    df_preds_ceo = df_preds_ceo.drop_duplicates(subset=["unique_id_l"], keep="first")
    print(f"  After dedup (best per person): {df_preds_ceo.shape[0]:,}")

    # join back to get original names and gvkey
    df_preds_ceo = df_preds_ceo.merge(
        persons_unique[["unique_id", "name"]].rename(columns={"unique_id": "unique_id_l", "name": "person_name"}),
        on="unique_id_l", how="left"
    )
    df_preds_ceo = df_preds_ceo.merge(
        ceo_unique[["unique_id", "exec_fullname", "gvkey", "coname"]].rename(columns={"unique_id": "unique_id_r"}),
        on="unique_id_r", how="left"
    )

    # join back to market_id level
    person_market = market_names[market_names["type"] == "person"][["market_id", "name"]].rename(
        columns={"name": "person_name"})
    key_ceo = person_market.merge(
        df_preds_ceo[["person_name", "exec_fullname", "gvkey", "coname", "match_probability"]],
        on="person_name", how="inner"
    )
    key_ceo = key_ceo.rename(columns={"exec_fullname": "ceo_name"})
else:
    key_ceo = pd.DataFrame(columns=["market_id", "person_name", "ceo_name", "gvkey", "coname", "match_probability"])

print(f"  key_market_ceo: {key_ceo.shape[0]:,} rows ({key_ceo['market_id'].nunique():,} markets)")
key_ceo.to_parquet(os.path.join(DATA_TEMP, "key_market_ceo.parquet"), index=False)
print("  Saved: key_market_ceo.parquet")

# ==============================================================
#  Step D: Splink fuzzy merge — company names → Compustat
# ==============================================================
"""
Left:  unique company names from polymarket
Right: unique conm from Compustat
Match on normalized name via Jaro-Winkler
"""
print("\n" + "="*60)
print("  Step D: Company → Compustat matching (splink)")
print("="*60)

companies_unique = (market_names[market_names["type"] == "company"][["name"]]
                    .drop_duplicates().reset_index(drop=True))
companies_unique["unique_id"] = range(len(companies_unique))
companies_unique["name_clean"] = companies_unique["name"].apply(normalize_name)
companies_unique = companies_unique[companies_unique["name_clean"].str.len() > 1].reset_index(drop=True)

comp_match = comp_ref[["gvkey", "conm"]].copy()
comp_match["unique_id"] = range(len(comp_match))
comp_match["name_clean"] = comp_match["conm"].apply(normalize_name)
comp_match = comp_match[comp_match["name_clean"].str.len() > 1].reset_index(drop=True)

print(f"  Left (companies): {len(companies_unique):,} unique names")
print(f"  Right (compustat): {len(comp_match):,} unique firms")

df_l_comp = companies_unique[["unique_id", "name_clean"]].rename(columns={"name_clean": "name_norm"})
df_r_comp = comp_match[["unique_id", "name_clean"]].rename(columns={"name_clean": "name_norm"})

settings_comp = SettingsCreator(
    link_type="link_only",
    comparisons=[cl.JaroWinklerAtThresholds("name_norm", [0.92, 0.85])],
    blocking_rules_to_generate_predictions=[
        "substr(l.name_norm,1,1) = substr(r.name_norm,1,1)"
    ],
    probability_two_random_records_match=0.01,
)

linker_comp = Linker([df_l_comp, df_r_comp], settings_comp, DuckDBAPI(),
                     input_table_aliases=["polymarket_companies", "wrds_compustat"])
linker_comp.training.estimate_u_using_random_sampling(max_pairs=1e6)

preds_comp = linker_comp.inference.predict(threshold_match_probability=0.1)
df_preds_comp = preds_comp.as_pandas_dataframe()
print(f"  Raw matches: {df_preds_comp.shape[0]:,}")

if len(df_preds_comp) > 0:
    df_preds_comp = df_preds_comp.sort_values("match_probability", ascending=False)
    df_preds_comp = df_preds_comp.drop_duplicates(subset=["unique_id_l"], keep="first")
    print(f"  After dedup (best per company): {df_preds_comp.shape[0]:,}")

    df_preds_comp = df_preds_comp.merge(
        companies_unique[["unique_id", "name"]].rename(columns={"unique_id": "unique_id_l", "name": "company_name"}),
        on="unique_id_l", how="left"
    )
    df_preds_comp = df_preds_comp.merge(
        comp_match[["unique_id", "gvkey", "conm"]].rename(columns={"unique_id": "unique_id_r"}),
        on="unique_id_r", how="left"
    )

    company_market = market_names[market_names["type"] == "company"][["market_id", "name"]].rename(
        columns={"name": "company_name"})
    key_company = company_market.merge(
        df_preds_comp[["company_name", "gvkey", "conm", "match_probability"]],
        on="company_name", how="inner"
    )
else:
    key_company = pd.DataFrame(columns=["market_id", "company_name", "gvkey", "conm", "match_probability"])

print(f"  key_market_company: {key_company.shape[0]:,} rows ({key_company['market_id'].nunique():,} markets)")
key_company.to_parquet(os.path.join(DATA_TEMP, "key_market_company.parquet"), index=False)
print("  Saved: key_market_company.parquet")

# ==============================================================
#  Step E: Consolidate → temp/key_market_company_full.parquet
# ==============================================================
"""
Merge both key files at (market_id, gvkey) level
- i_mention = 2 if matched from both CEO and company, 1 if either only
- mentioned_ceo = 1 if ceo_name is non-empty, 0 otherwise
"""
print("\n" + "="*60)
print("  Step E: Consolidate")
print("="*60)

# from CEO matches
ceo_agg = key_ceo.groupby(["market_id", "gvkey"]).agg(
    person_name=("person_name", "first"),
    ceo_name=("ceo_name", "first"),
    coname_ceo=("coname", "first"),
).reset_index()
ceo_agg["source_ceo"] = 1

# from company matches
comp_agg = key_company.groupby(["market_id", "gvkey"]).agg(
    company_name=("company_name", "first"),
    conm=("conm", "first"),
).reset_index()
comp_agg["source_company"] = 1

# full outer join
full = pd.merge(ceo_agg, comp_agg, on=["market_id", "gvkey"], how="outer")
full["source_ceo"] = full["source_ceo"].fillna(0).astype(int)
full["source_company"] = full["source_company"].fillna(0).astype(int)
full["i_mention"] = full["source_ceo"] + full["source_company"]
full["mentioned_ceo"] = (full["ceo_name"].notna()).astype(int)

# coalesce coname
full["coname"] = full["coname_ceo"].fillna(full["conm"])
full = full.drop(columns=["coname_ceo", "conm", "source_ceo", "source_company"])

print(f"  Full key: {full.shape[0]:,} rows ({full['market_id'].nunique():,} markets, {full['gvkey'].nunique():,} firms)")
print(f"  i_mention distribution:")
print(full["i_mention"].value_counts().to_string())
print(f"  mentioned_ceo: {full['mentioned_ceo'].sum():,}")

full.to_parquet(os.path.join(DATA_TEMP, "key_market_company_full.parquet"), index=False)
print("  Saved: key_market_company_full.parquet")

# ==============================================================
#  Quality check: sample matches
# ==============================================================
print("\n" + "="*60)
print("  Sample matches (top probability)")
print("="*60)

if len(key_ceo) > 0:
    print("\n  CEO matches (top 10):")
    sample_ceo = key_ceo.drop_duplicates("person_name").nlargest(10, "match_probability")
    for _, row in sample_ceo.iterrows():
        print(f"    {row['person_name']:30s} → {row['ceo_name']:30s} ({row['coname']}) p={row['match_probability']:.3f}")

if len(key_company) > 0:
    print("\n  Company matches (top 10):")
    sample_comp = key_company.drop_duplicates("company_name").nlargest(10, "match_probability")
    for _, row in sample_comp.iterrows():
        print(f"    {row['company_name']:30s} → {row['conm']:30s} (gvkey={row['gvkey']}) p={row['match_probability']:.3f}")

print("\nDone.")
