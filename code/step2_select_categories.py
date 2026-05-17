# ****************************************************
# step2_select_categories.py
# Input  : temp/markets_categories_entities.parquet
# Output : temp/markets_categories_entities_selected.parquet
# ****************************************************

import os
import pandas as pd

from config import DATA_TEMP

"""
Load
"""
df = pd.read_parquet(os.path.join(DATA_TEMP, "markets_categories_entities.parquet"))
print(f"All categories: {df.shape[0]:,} rows")
print(df["category_llm"].value_counts())

"""
Select target categories
"""
KEEP_CATS = ["business", "tech", "commodities", "culture", "science"]

df_sel = df[df["category_llm"].isin(KEEP_CATS)].reset_index(drop=True)
print(f"\nSelected: {df_sel.shape[0]:,} rows")
print(df_sel["category_llm"].value_counts())

"""
Save
"""
df_sel.to_parquet(os.path.join(DATA_TEMP, "markets_categories_entities_selected.parquet"), index=False)
print(f"\nSaved: markets_categories_entities_selected.parquet")
