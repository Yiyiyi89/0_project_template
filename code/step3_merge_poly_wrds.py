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
import duckdb

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
    s = re.sub(r"[.,'\-]", " ", s)
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
CEO reference: unique (exec_fullname, gvkey, coname)
Company reference: unique (gvkey, conm) from compustat
"""
ceo_raw = pd.read_parquet(os.path.join(DATA_RAW_WRDS, "ceo_fm_yr.parquet"))
ceo_raw["year"] = ceo_raw["year"].astype(int)
ceo_ref = (ceo_raw[["gvkey", "exec_fullname", "coname"]]
           .drop_duplicates(subset=["gvkey", "exec_fullname"])
           .reset_index(drop=True))
print(f"\nCEO reference: {ceo_ref.shape[0]:,} unique (gvkey, ceo_name) pairs")

comp_raw = pd.read_parquet(os.path.join(DATA_RAW_WRDS, "compustat_fm_qt.parquet"),
                           columns=["gvkey", "conm"])
comp_ref = comp_raw.drop_duplicates(subset=["gvkey"]).reset_index(drop=True)
print(f"Company reference: {comp_ref.shape[0]:,} unique (gvkey, conm)")

# ==============================================================
#  Step C: Person → CEO matching
# ==============================================================
"""
Tier 1 (best):  exact normalized name OR JW >= 0.92 with surname-initial blocking
Tier 2 (secondary): JW >= 0.85 with first+last initial blocking
"""
print("\n" + "="*60)
print("  Step C: Person → CEO matching")
print("="*60)

persons_unique = (market_names[market_names["type"] == "person"][["name"]]
                  .drop_duplicates().reset_index(drop=True))
persons_unique["name_clean"] = persons_unique["name"].apply(normalize_name)
persons_unique = persons_unique[persons_unique["name_clean"].str.len() > 2].reset_index(drop=True)

ceo_names = ceo_ref[["exec_fullname", "gvkey", "coname"]].copy()
ceo_names["name_clean"] = ceo_names["exec_fullname"].apply(normalize_name)
ceo_names = ceo_names[ceo_names["name_clean"].str.len() > 2].reset_index(drop=True)

print(f"  Left (persons): {len(persons_unique):,}")
print(f"  Right (CEOs):   {len(ceo_names):,}")

# --- Tier 1: exact match ---
exact_ceo = persons_unique.merge(
    ceo_names, on="name_clean", how="inner"
).rename(columns={"exec_fullname": "ceo_name"})
exact_ceo["match_tier"] = 1
exact_ceo["match_method"] = "exact"
exact_ceo["match_score"] = 1.0
print(f"  Tier 1 exact: {exact_ceo['name'].nunique():,} persons")

# --- Tier 1: JW >= 0.95 + last-name check ---
matched_t1 = set(exact_ceo["name"].unique())
unmatched_ceo = persons_unique[~persons_unique["name"].isin(matched_t1)].copy()
unmatched_ceo = unmatched_ceo[unmatched_ceo["name_clean"].str.len() >= 5].reset_index(drop=True)

con = duckdb.connect()
con.execute("CREATE TABLE poly_persons AS SELECT * FROM unmatched_ceo")
con.execute("CREATE TABLE wrds_ceos AS SELECT * FROM ceo_names")

jw_t1 = con.execute("""
    SELECT p.name, p.name_clean as p_clean,
           c.exec_fullname as ceo_name, c.name_clean as c_clean,
           c.gvkey, c.coname,
           jaro_winkler_similarity(p.name_clean, c.name_clean) as jw_score
    FROM poly_persons p, wrds_ceos c
    WHERE substr(p.name_clean, 1, 1) = substr(c.name_clean, 1, 1)
      AND substr(split_part(p.name_clean, ' ', -1), 1, 1)
        = substr(split_part(c.name_clean, ' ', -1), 1, 1)
      AND jaro_winkler_similarity(p.name_clean, c.name_clean) >= 0.92
""").fetchdf()

if len(jw_t1) > 0:
    jw_t1 = jw_t1.sort_values("jw_score", ascending=False).drop_duplicates("name", keep="first")
    # post-filter: last token of poly name must match last token of CEO name
    def surname_match(row):
        p_last = row["p_clean"].split()[-1] if row["p_clean"].split() else ""
        c_last = row["c_clean"].split()[-1] if row["c_clean"].split() else ""
        if len(p_last) < 3 or len(c_last) < 3:
            return False
        return p_last == c_last or p_last in c_last or c_last in p_last
    jw_t1 = jw_t1[jw_t1.apply(surname_match, axis=1)].reset_index(drop=True)
    jw_t1["name_clean"] = jw_t1["p_clean"]
    jw_t1["match_tier"] = 1
    jw_t1["match_method"] = "jw_strict"
    jw_t1["match_score"] = jw_t1["jw_score"]
    jw_t1 = jw_t1[["name", "name_clean", "ceo_name", "gvkey", "coname", "match_tier", "match_method", "match_score"]]
    matched_t1.update(jw_t1["name"].unique())
    print(f"  Tier 1 JW>=0.95 + surname: {jw_t1['name'].nunique():,} persons")
else:
    jw_t1 = pd.DataFrame(columns=["name", "name_clean", "ceo_name", "gvkey", "coname", "match_tier", "match_method", "match_score"])

# --- Tier 2: JW >= 0.88, first-char blocking (secondary candidates) ---
unmatched_ceo2 = persons_unique[~persons_unique["name"].isin(matched_t1)].copy()
unmatched_ceo2 = unmatched_ceo2[unmatched_ceo2["name_clean"].str.len() >= 5].reset_index(drop=True)

con.execute("DROP TABLE IF EXISTS poly_persons")
con.execute("CREATE TABLE poly_persons AS SELECT * FROM unmatched_ceo2")

jw_t2 = con.execute("""
    SELECT p.name, p.name_clean as p_clean,
           c.exec_fullname as ceo_name, c.name_clean as c_clean,
           c.gvkey, c.coname,
           jaro_winkler_similarity(p.name_clean, c.name_clean) as jw_score
    FROM poly_persons p, wrds_ceos c
    WHERE substr(p.name_clean, 1, 1) = substr(c.name_clean, 1, 1)
      AND substr(split_part(p.name_clean, ' ', -1), 1, 1)
        = substr(split_part(c.name_clean, ' ', -1), 1, 1)
      AND jaro_winkler_similarity(p.name_clean, c.name_clean) >= 0.85
""").fetchdf()
con.close()

if len(jw_t2) > 0:
    jw_t2 = jw_t2.sort_values("jw_score", ascending=False).drop_duplicates("name", keep="first")
    jw_t2["name_clean"] = jw_t2["p_clean"]
    jw_t2["match_tier"] = 2
    jw_t2["match_method"] = "jw_loose"
    jw_t2["match_score"] = jw_t2["jw_score"]
    jw_t2 = jw_t2[["name", "name_clean", "ceo_name", "gvkey", "coname", "match_tier", "match_method", "match_score"]]
    print(f"  Tier 2 JW>=0.88: {jw_t2['name'].nunique():,} persons")
else:
    jw_t2 = pd.DataFrame(columns=["name", "name_clean", "ceo_name", "gvkey", "coname", "match_tier", "match_method", "match_score"])

# Combine CEO matches
all_ceo_matches = pd.concat([
    exact_ceo[["name", "name_clean", "ceo_name", "gvkey", "coname", "match_tier", "match_method", "match_score"]],
    jw_t1, jw_t2
], ignore_index=True)

# Join back to market_id
person_market = market_names[market_names["type"] == "person"][["market_id", "name"]].rename(
    columns={"name": "person_name"})
key_ceo = person_market.merge(
    all_ceo_matches.rename(columns={"name": "person_name"})[
        ["person_name", "ceo_name", "gvkey", "coname", "match_tier", "match_method", "match_score"]],
    on="person_name", how="inner"
)

print(f"  Total key_market_ceo: {key_ceo.shape[0]:,} rows ({key_ceo['market_id'].nunique():,} markets)")
print(f"    Tier 1: {key_ceo[key_ceo['match_tier']==1].shape[0]:,} rows")
print(f"    Tier 2: {key_ceo[key_ceo['match_tier']==2].shape[0]:,} rows")
key_ceo.to_parquet(os.path.join(DATA_TEMP, "key_market_ceo.parquet"), index=False)
print("  Saved: key_market_ceo.parquet")

# ==============================================================
#  Step D: Company → Compustat matching
# ==============================================================
"""
Tier 1 (best):  exact normalized OR JW >= 0.95 OR starts-with match
Tier 2 (secondary): JW >= 0.85 OR token-containment OR substring (>=6 chars)
"""
print("\n" + "="*60)
print("  Step D: Company → Compustat matching")
print("="*60)

companies_unique = (market_names[market_names["type"] == "company"][["name"]]
                    .drop_duplicates().reset_index(drop=True))
companies_unique["name_clean"] = companies_unique["name"].apply(normalize_name)
companies_unique = companies_unique[companies_unique["name_clean"].str.len() > 1].reset_index(drop=True)

comp_match = comp_ref[["gvkey", "conm"]].copy()
comp_match["name_clean"] = comp_match["conm"].apply(normalize_name)
comp_match = comp_match[comp_match["name_clean"].str.len() > 1].reset_index(drop=True)

print(f"  Left (companies): {len(companies_unique):,}")
print(f"  Right (compustat): {len(comp_match):,}")

# --- Tier 1: exact normalized match ---
exact_comp = companies_unique.merge(comp_match, on="name_clean", how="inner")
exact_comp["match_tier"] = 1
exact_comp["match_method"] = "exact"
exact_comp["match_score"] = 1.0
matched_t1_comp = set(exact_comp["name"].unique())
print(f"  Tier 1 exact: {len(matched_t1_comp):,} companies")

# --- Tier 1: starts-with (compustat name starts with polymarket name, poly >= 5 chars) ---
unmatched_c1 = companies_unique[~companies_unique["name"].isin(matched_t1_comp)].copy()
unmatched_c1 = unmatched_c1[unmatched_c1["name_clean"].str.len() >= 5].reset_index(drop=True)

startswith_matches = []
for _, row in unmatched_c1.iterrows():
    pname = row["name_clean"]
    hits = comp_match[comp_match["name_clean"].str.startswith(pname + " ") |
                      (comp_match["name_clean"] == pname)]
    if len(hits) > 0:
        # prefer shortest name (closest match to input)
        best = hits.loc[hits["name_clean"].str.len().idxmin()]
        startswith_matches.append({
            "name": row["name"], "name_clean": row["name_clean"],
            "gvkey": best["gvkey"], "conm": best["conm"],
            "match_tier": 1, "match_method": "starts_with", "match_score": 0.97,
        })

if startswith_matches:
    sw_comp = pd.DataFrame(startswith_matches)
    matched_t1_comp.update(sw_comp["name"].unique())
    print(f"  Tier 1 starts-with: {len(sw_comp):,} companies")
else:
    sw_comp = pd.DataFrame(columns=["name", "name_clean", "gvkey", "conm", "match_tier", "match_method", "match_score"])

# --- Tier 1: JW >= 0.95 (high confidence fuzzy) ---
unmatched_c2 = companies_unique[~companies_unique["name"].isin(matched_t1_comp)].copy()
unmatched_c2 = unmatched_c2[unmatched_c2["name_clean"].str.len() >= 5].reset_index(drop=True)

if len(unmatched_c2) > 0:
    con = duckdb.connect()
    con.execute("CREATE TABLE poly_co AS SELECT * FROM unmatched_c2")
    con.execute("CREATE TABLE wrds_co AS SELECT * FROM comp_match")

    jw_t1_comp = con.execute("""
        SELECT p.name, p.name_clean as p_clean,
               c.gvkey, c.conm, c.name_clean as c_clean,
               jaro_winkler_similarity(p.name_clean, c.name_clean) as jw_score
        FROM poly_co p, wrds_co c
        WHERE substr(p.name_clean, 1, 1) = substr(c.name_clean, 1, 1)
          AND jaro_winkler_similarity(p.name_clean, c.name_clean) >= 0.95
    """).fetchdf()
    con.close()

    if len(jw_t1_comp) > 0:
        jw_t1_comp = jw_t1_comp.sort_values("jw_score", ascending=False).drop_duplicates("name", keep="first")
        jw_t1_comp["name_clean"] = jw_t1_comp["p_clean"]
        jw_t1_comp["match_tier"] = 1
        jw_t1_comp["match_method"] = "jw_strict"
        jw_t1_comp["match_score"] = jw_t1_comp["jw_score"]
        jw_t1_comp = jw_t1_comp[["name", "name_clean", "gvkey", "conm", "match_tier", "match_method", "match_score"]]
        matched_t1_comp.update(jw_t1_comp["name"].unique())
        print(f"  Tier 1 JW>=0.95: {len(jw_t1_comp):,} companies")
    else:
        jw_t1_comp = pd.DataFrame(columns=["name", "name_clean", "gvkey", "conm", "match_tier", "match_method", "match_score"])
else:
    jw_t1_comp = pd.DataFrame(columns=["name", "name_clean", "gvkey", "conm", "match_tier", "match_method", "match_score"])

# --- Tier 2: JW >= 0.85 (secondary candidates) ---
unmatched_c3 = companies_unique[~companies_unique["name"].isin(matched_t1_comp)].copy()
unmatched_c3 = unmatched_c3[unmatched_c3["name_clean"].str.len() >= 5].reset_index(drop=True)

if len(unmatched_c3) > 0:
    con = duckdb.connect()
    con.execute("CREATE TABLE poly_co AS SELECT * FROM unmatched_c3")
    con.execute("CREATE TABLE wrds_co AS SELECT * FROM comp_match")

    jw_t2_comp = con.execute("""
        SELECT p.name, p.name_clean as p_clean,
               c.gvkey, c.conm, c.name_clean as c_clean,
               jaro_winkler_similarity(p.name_clean, c.name_clean) as jw_score
        FROM poly_co p, wrds_co c
        WHERE substr(p.name_clean, 1, 1) = substr(c.name_clean, 1, 1)
          AND jaro_winkler_similarity(p.name_clean, c.name_clean) >= 0.85
    """).fetchdf()
    con.close()

    if len(jw_t2_comp) > 0:
        jw_t2_comp = jw_t2_comp.sort_values("jw_score", ascending=False).drop_duplicates("name", keep="first")
        # short names (< 7 chars) need >= 0.92 to avoid garbage
        short_mask = (jw_t2_comp["p_clean"].str.len() < 7) & (jw_t2_comp["jw_score"] < 0.92)
        jw_t2_comp = jw_t2_comp[~short_mask].reset_index(drop=True)
        jw_t2_comp["name_clean"] = jw_t2_comp["p_clean"]
        jw_t2_comp["match_tier"] = 2
        jw_t2_comp["match_method"] = "jw_loose"
        jw_t2_comp["match_score"] = jw_t2_comp["jw_score"]
        jw_t2_comp = jw_t2_comp[["name", "name_clean", "gvkey", "conm", "match_tier", "match_method", "match_score"]]
        print(f"  Tier 2 JW>=0.85: {len(jw_t2_comp):,} companies")
    else:
        jw_t2_comp = pd.DataFrame(columns=["name", "name_clean", "gvkey", "conm", "match_tier", "match_method", "match_score"])
else:
    jw_t2_comp = pd.DataFrame(columns=["name", "name_clean", "gvkey", "conm", "match_tier", "match_method", "match_score"])

# --- Tier 2: token containment (poly tokens ⊆ ref, ref starts with poly token for single-word) ---
matched_all_comp = matched_t1_comp | set(jw_t2_comp["name"].unique()) if len(jw_t2_comp) > 0 else matched_t1_comp
unmatched_c4 = companies_unique[~companies_unique["name"].isin(matched_all_comp)].copy()
unmatched_c4 = unmatched_c4[unmatched_c4["name_clean"].str.len() >= 4].reset_index(drop=True)

comp_match_tokens = comp_match.copy()
comp_match_tokens["tokens"] = comp_match_tokens["name_clean"].apply(lambda s: set(s.split()))

token_matches = []
for _, row in unmatched_c4.iterrows():
    poly_tokens = set(row["name_clean"].split())
    if len(poly_tokens) == 0:
        continue
    for _, ref_row in comp_match_tokens.iterrows():
        ref_tokens = ref_row["tokens"]
        if not poly_tokens.issubset(ref_tokens):
            continue
        # single-word: ref must start with it
        if len(poly_tokens) == 1:
            if not ref_row["name_clean"].startswith(list(poly_tokens)[0]):
                continue
        # multi-word: poly must cover >= 50% of ref tokens
        elif len(poly_tokens) / len(ref_tokens) < 0.5:
            continue
        token_matches.append({
            "name": row["name"], "name_clean": row["name_clean"],
            "gvkey": ref_row["gvkey"], "conm": ref_row["conm"],
            "match_tier": 2, "match_method": "token_contain", "match_score": 0.90,
        })
        break

if token_matches:
    tk_comp = pd.DataFrame(token_matches)
    print(f"  Tier 2 token-contain: {len(tk_comp):,} companies")
else:
    tk_comp = pd.DataFrame(columns=["name", "name_clean", "gvkey", "conm", "match_tier", "match_method", "match_score"])

# Combine all company matches
all_comp_matches = pd.concat([
    exact_comp[["name", "name_clean", "gvkey", "conm", "match_tier", "match_method", "match_score"]],
    sw_comp, jw_t1_comp, jw_t2_comp, tk_comp
], ignore_index=True)

# Join back to market_id
company_market = market_names[market_names["type"] == "company"][["market_id", "name"]].rename(
    columns={"name": "company_name"})
key_company = company_market.merge(
    all_comp_matches.rename(columns={"name": "company_name"})[
        ["company_name", "gvkey", "conm", "match_tier", "match_method", "match_score"]],
    on="company_name", how="inner"
)

print(f"  Total key_market_company: {key_company.shape[0]:,} rows ({key_company['market_id'].nunique():,} markets)")
print(f"    Tier 1: {key_company[key_company['match_tier']==1].shape[0]:,} rows")
print(f"    Tier 2: {key_company[key_company['match_tier']==2].shape[0]:,} rows")
key_company.to_parquet(os.path.join(DATA_TEMP, "key_market_company.parquet"), index=False)
print("  Saved: key_market_company.parquet")

# ==============================================================
#  Step E: Consolidate → temp/key_market_company_full.parquet
# ==============================================================
"""
Merge both key files at (market_id, gvkey) level
- match_tier = min tier across sources (best match wins)
- i_mention = 2 if matched from both CEO and company, 1 if either only
- mentioned_ceo = 1 if ceo_name is non-empty, 0 otherwise
"""
print("\n" + "="*60)
print("  Step E: Consolidate")
print("="*60)

ceo_agg = key_ceo.groupby(["market_id", "gvkey"]).agg(
    person_name=("person_name", "first"),
    ceo_name=("ceo_name", "first"),
    coname_ceo=("coname", "first"),
    ceo_tier=("match_tier", "min"),
).reset_index()
ceo_agg["source_ceo"] = 1

comp_agg = key_company.groupby(["market_id", "gvkey"]).agg(
    company_name=("company_name", "first"),
    conm=("conm", "first"),
    comp_tier=("match_tier", "min"),
).reset_index()
comp_agg["source_company"] = 1

full = pd.merge(ceo_agg, comp_agg, on=["market_id", "gvkey"], how="outer")
full["source_ceo"] = full["source_ceo"].fillna(0).astype(int)
full["source_company"] = full["source_company"].fillna(0).astype(int)
full["i_mention"] = full["source_ceo"] + full["source_company"]
full["mentioned_ceo"] = (full["ceo_name"].notna()).astype(int)
full["match_tier"] = full[["ceo_tier", "comp_tier"]].min(axis=1).astype(int)

full["coname"] = full["coname_ceo"].fillna(full["conm"])
full = full.drop(columns=["coname_ceo", "conm", "source_ceo", "source_company", "ceo_tier", "comp_tier"])

print(f"  Full key: {full.shape[0]:,} rows ({full['market_id'].nunique():,} markets, {full['gvkey'].nunique():,} firms)")
print(f"  By tier:")
print(full["match_tier"].value_counts().sort_index().to_string())
print(f"  i_mention distribution:")
print(full["i_mention"].value_counts().to_string())

full.to_parquet(os.path.join(DATA_TEMP, "key_market_company_full.parquet"), index=False)
print("  Saved: key_market_company_full.parquet")

# ==============================================================
#  Quality check
# ==============================================================
print("\n" + "="*60)
print("  Quality Check — Tier 1 (best matches)")
print("="*60)

t1_ceo = all_ceo_matches[all_ceo_matches["match_tier"]==1]
if len(t1_ceo) > 0:
    print(f"\n  CEO Tier 1: {t1_ceo['name'].nunique():,} unique persons")
    print(f"  Methods: {t1_ceo['match_method'].value_counts().to_dict()}")
    print("  Sample:")
    for _, row in t1_ceo.head(15).iterrows():
        print(f"    {row['name']:30s} → {row['ceo_name']:30s} ({row['coname']}) [{row['match_method']}, s={row['match_score']:.3f}]")

t1_comp = all_comp_matches[all_comp_matches["match_tier"]==1]
if len(t1_comp) > 0:
    print(f"\n  Company Tier 1: {t1_comp['name'].nunique():,} unique companies")
    print(f"  Methods: {t1_comp['match_method'].value_counts().to_dict()}")
    print("  Sample (starts_with + jw_strict):")
    non_exact = t1_comp[t1_comp["match_method"] != "exact"]
    for _, row in non_exact.head(20).iterrows():
        print(f"    {row['name']:30s} → {row['conm']:35s} [{row['match_method']}, s={row['match_score']:.3f}]")

print("\n" + "="*60)
print("  Quality Check — Tier 2 (secondary candidates)")
print("="*60)

t2_ceo = all_ceo_matches[all_ceo_matches["match_tier"]==2]
if len(t2_ceo) > 0:
    print(f"\n  CEO Tier 2: {t2_ceo['name'].nunique():,} unique persons")
    print("  Sample (lowest scores):")
    for _, row in t2_ceo.nsmallest(20, "match_score").iterrows():
        print(f"    {row['name']:30s} → {row['ceo_name']:30s} ({row['coname']}) s={row['match_score']:.3f}")

t2_comp = all_comp_matches[all_comp_matches["match_tier"]==2]
if len(t2_comp) > 0:
    print(f"\n  Company Tier 2: {t2_comp['name'].nunique():,} unique companies")
    print("  Sample (lowest scores):")
    for _, row in t2_comp.nsmallest(20, "match_score").iterrows():
        print(f"    {row['name']:30s} → {row['conm']:35s} [{row['match_method']}, s={row['match_score']:.3f}]")

# Coverage
total_p = market_names[market_names["type"]=="person"]["name"].nunique()
total_c = market_names[market_names["type"]=="company"]["name"].nunique()
t1p = t1_ceo["name"].nunique() if len(t1_ceo) > 0 else 0
t2p = t2_ceo["name"].nunique() if len(t2_ceo) > 0 else 0
t1c = t1_comp["name"].nunique() if len(t1_comp) > 0 else 0
t2c = t2_comp["name"].nunique() if len(t2_comp) > 0 else 0
print(f"\n  COVERAGE:")
print(f"    Persons:   Tier1={t1p:,} ({t1p/total_p*100:.1f}%)  Tier2={t2p:,} ({t2p/total_p*100:.1f}%)  Total={t1p+t2p:,} ({(t1p+t2p)/total_p*100:.1f}%)")
print(f"    Companies: Tier1={t1c:,} ({t1c/total_c*100:.1f}%)  Tier2={t2c:,} ({t2c/total_c*100:.1f}%)  Total={t1c+t2c:,} ({(t1c+t2c)/total_c*100:.1f}%)")

print("\nDone.")
