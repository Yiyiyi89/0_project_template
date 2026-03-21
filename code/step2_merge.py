# ****************************************************
# step2_merge.py
# Input  : temp/[data]_[level].parquet
# Output : temp/key_[data1]_[data2].parquet
#            e.g. key_revelio_aa.parquet
# ****************************************************

import os
import pandas as pd
import numpy as np

from config import DATA_TEMP

"""
Load
"""
df_main = pd.read_parquet(os.path.join(DATA_TEMP, "revelio_firm_year.parquet"))
df_key  = pd.read_parquet(os.path.join(DATA_TEMP, "aa_state_year.parquet"))

print(f"main : {df_main.shape[0]:,} rows")
print(f"key  : {df_key.shape[0]:,} rows")

"""
Merge
"""
df = pd.merge(df_main, df_key, how="left", on="id")

# merge diagnostics
n_matched   = df["key_col"].notna().sum()
n_unmatched = df["key_col"].isna().sum()
print(f"Matched  : {n_matched:,}")
print(f"Unmatched: {n_unmatched:,}")

"""
Post-merge cleaning
"""
# df = df.drop(columns=["redundant_col"])
# df = df.rename(columns={"col_x": "col"})

"""
Save
Naming convention: temp/key_[data1]_[data2].parquet
  e.g. key_revelio_aa.parquet
"""
df.to_parquet(os.path.join(DATA_TEMP, "key_revelio_aa.parquet"), index=False)
print("Saved to DATA_TEMP")
