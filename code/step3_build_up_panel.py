# ****************************************************
# step3_build_up_panel.py
# Input  : temp/key_[data1]_[data2].parquet
#          temp/[data]_[level].parquet
# Output : output/panel_[level].parquet
#            e.g. panel_firm_year.parquet
#                 panel_state_year.parquet
# ****************************************************

import os
import pandas as pd
import numpy as np

from config import DATA_TEMP, DATA_OUTPUT

"""
Load
"""
df_panel = pd.read_parquet(os.path.join(DATA_TEMP, "revelio_firm_year.parquet"))
df_key   = pd.read_parquet(os.path.join(DATA_TEMP, "key_revelio_aa.parquet"))

print(f"panel: {df_panel.shape[0]:,} rows  |  key: {df_key.shape[0]:,} rows")

"""
Build panel (entity x time)
"""
ENTITY = "firm_id"
TIME   = "year"

# merge key onto panel variables
df = pd.merge(df_panel, df_key, how="left", on=ENTITY)

# complete the panel: all entity-year combinations
entities = df[ENTITY].unique()
years    = range(df[TIME].min(), df[TIME].max() + 1)
panel_index = pd.MultiIndex.from_product([entities, years], names=[ENTITY, TIME])
panel = pd.DataFrame(index=panel_index).reset_index()

df = pd.merge(panel, df, how="left", on=[ENTITY, TIME])

print(f"Panel rows: {df.shape[0]:,}  ({df[ENTITY].nunique()} entities x {df[TIME].nunique()} years)")

"""
Construct variables
"""
# df["log_var"] = np.log(df["var"] + 1)

# lag / lead
# df = df.sort_values([ENTITY, TIME])
# df["lag_var"] = df.groupby(ENTITY)["var"].shift(1)

# within-group aggregation
# df["var_mean"] = df.groupby(ENTITY)["var"].transform("mean")

"""
Save
Naming convention: output/panel_[level].parquet
  e.g. panel_firm_year.parquet
       panel_state_year.parquet
"""
df.to_parquet(os.path.join(DATA_OUTPUT, "panel_firm_year.parquet"), index=False)
print("Saved to DATA_OUTPUT")
