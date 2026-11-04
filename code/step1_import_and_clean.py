# ****************************************************
# step1_import_and_clean.py
# Input  : input/[raw_data]
# Output : temp/[data]_[level].parquet
#            e.g. revelio_firm_year.parquet
#                 aa_state_year.parquet
# ****************************************************

import os
import pandas as pd
import numpy as np

from config import DATA_INPUT, DATA_TEMP

"""
Import
"""
df = pd.read_csv(os.path.join(DATA_INPUT, "raw_data.csv"))
# df = pd.read_stata(os.path.join(DATA_INPUT, "raw_data.dta"))
# df = pd.read_csv(os.path.join(DATA_INPUT, "raw_data.csv.gz"), compression="gzip")

print(f"Loaded: {df.shape[0]:,} rows x {df.shape[1]} cols")
print(df.dtypes)

"""
Clean
"""
# drop duplicates
df = df.drop_duplicates()

# rename columns
# df = df.rename(columns={"old_name": "new_name"})

# convert types
# df["date_col"] = pd.to_datetime(df["date_col"])
# df["id_col"]   = df["id_col"].astype(str)

# drop / fill missing
# df = df.dropna(subset=["key_col"])
# df["col"] = df["col"].fillna(0)

# filter rows
# df = df[df["year"] >= 2000]

"""
Save
Naming convention: temp/[data]_[level].parquet
  e.g. revelio_firm_year.parquet
       aa_state_year.parquet
"""
df.to_parquet(os.path.join(DATA_TEMP, "revelio_firm_year.parquet"), index=False)
# df.to_parquet(os.path.join(DATA_TEMP, "aa_state_year.parquet"), index=False)
print("Saved to DATA_TEMP")
