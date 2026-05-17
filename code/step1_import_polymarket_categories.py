# ****************************************************
# step1_import_polymarket_categories.py
# Input  : temp/markets_categories_entities.parquet
#          raw/markets.parquet
# Output : output/category_report.txt
#          output/fig_category_pct.png
#          output/fig_subcategory_business.png
#          output/fig_time_trend_all.png
#          output/fig_top_companies_business.png
#          output/fig_top_persons_politics.png
# ****************************************************

import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from collections import Counter

from config import DATA_TEMP, DATA_OUTPUT, PARENT

DATA_RAW = PARENT / "data" / "raw"

plt.rcParams.update({"figure.dpi": 150, "figure.figsize": (10, 6)})

os.makedirs(DATA_OUTPUT, exist_ok=True)

"""
Load
"""
cats = pd.read_parquet(os.path.join(DATA_TEMP, "markets_categories_entities.parquet"))
markets = pd.read_parquet(os.path.join(DATA_RAW, "markets.parquet"), columns=["id", "createdAt"])

print(f"Categories: {cats.shape[0]:,} rows")
print(f"Markets:    {markets.shape[0]:,} rows")

merged = cats.merge(markets, on="id", how="left")
merged["month"] = merged["createdAt"].str[:7]

"""
1. Category Distribution
"""
cat_counts = cats["category_llm"].value_counts()
total = len(cats)
cat_pct = (cat_counts / total * 100).round(1)

# figure
fig, ax = plt.subplots(figsize=(10, 6))
cat_pct_sorted = cat_pct.sort_values(ascending=True)
bars = ax.barh(cat_pct_sorted.index, cat_pct_sorted.values, color="steelblue")
ax.set_xlabel("Percentage (%)")
ax.set_title(f"Category Distribution (N={total:,})")
for bar, val in zip(bars, cat_pct_sorted.values):
    ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
            f"{val:.1f}%", va="center", fontsize=9)
plt.tight_layout()
plt.savefig(os.path.join(DATA_OUTPUT, "fig_category_pct.png"))
plt.close()
print("Saved: fig_category_pct.png")

"""
2. Subcategory Distribution (for each target category)
"""
TARGET_CATS = ["politics", "culture", "tech", "economics",
               "geopolitics", "business", "commodities", "science"]

# business subcategory bar chart
biz = cats[cats["category_llm"] == "business"]
biz_sub = biz["subcategory_llm"].value_counts().head(10)

fig, ax = plt.subplots(figsize=(10, 5))
biz_sub_sorted = biz_sub.sort_values(ascending=True)
ax.barh(biz_sub_sorted.index, biz_sub_sorted.values, color="darkorange")
ax.set_xlabel("Count")
ax.set_title(f"Business Subcategories (N={len(biz):,})")
plt.tight_layout()
plt.savefig(os.path.join(DATA_OUTPUT, "fig_subcategory_business.png"))
plt.close()
print("Saved: fig_subcategory_business.png")

"""
3. Time Trends (monthly, all target categories)
"""
fig, ax = plt.subplots(figsize=(12, 7))
colors = plt.cm.tab10(np.linspace(0, 1, len(TARGET_CATS)))

for i, c in enumerate(TARGET_CATS):
    sub = merged[merged["category_llm"] == c]
    monthly = sub.groupby("month").size()
    monthly = monthly[monthly.index >= "2024-01"]
    ax.plot(range(len(monthly)), monthly.values, label=c, color=colors[i], linewidth=1.5)

ax.set_xlabel("Month (since 2024-01)")
ax.set_ylabel("Number of Markets Created")
ax.set_title("Monthly Market Creation by Category (2024+)")
ax.legend(loc="upper left", fontsize=8)
xtick_idx = list(range(0, 30, 3))
months_all = sorted(merged[merged["month"] >= "2024-01"]["month"].dropna().unique())
xtick_labels = [months_all[i] if i < len(months_all) else "" for i in xtick_idx]
ax.set_xticks(xtick_idx)
ax.set_xticklabels(xtick_labels, rotation=45, ha="right", fontsize=8)
plt.tight_layout()
plt.savefig(os.path.join(DATA_OUTPUT, "fig_time_trend_all.png"))
plt.close()
print("Saved: fig_time_trend_all.png")

"""
4. Top Companies in Business Category
"""
all_companies = []
for raw in biz["ner_companies"]:
    try:
        all_companies.extend(json.loads(raw))
    except:
        pass

comp_counts = Counter(all_companies)
top_comps = pd.Series(dict(comp_counts.most_common(20)))

fig, ax = plt.subplots(figsize=(10, 7))
top_comps_sorted = top_comps.sort_values(ascending=True)
ax.barh(top_comps_sorted.index, top_comps_sorted.values, color="seagreen")
ax.set_xlabel("Mentions")
ax.set_title(f"Top 20 Companies in Business Category (unique={len(comp_counts):,})")
plt.tight_layout()
plt.savefig(os.path.join(DATA_OUTPUT, "fig_top_companies_business.png"))
plt.close()
print("Saved: fig_top_companies_business.png")

"""
5. Top Persons in Politics Category
"""
pol = cats[cats["category_llm"] == "politics"]
all_persons = []
for raw in pol["ner_persons"]:
    try:
        all_persons.extend(json.loads(raw))
    except:
        pass

person_counts = Counter(all_persons)
top_persons = pd.Series(dict(person_counts.most_common(20)))

fig, ax = plt.subplots(figsize=(10, 7))
top_persons_sorted = top_persons.sort_values(ascending=True)
ax.barh(top_persons_sorted.index, top_persons_sorted.values, color="indianred")
ax.set_xlabel("Mentions")
ax.set_title(f"Top 20 Persons in Politics Category (unique={len(person_counts):,})")
plt.tight_layout()
plt.savefig(os.path.join(DATA_OUTPUT, "fig_top_persons_politics.png"))
plt.close()
print("Saved: fig_top_persons_politics.png")

"""
6. Full Text Report
"""
report_lines = []
report_lines.append(f"{'='*70}")
report_lines.append(f"POLYMARKET CATEGORY REPORT")
report_lines.append(f"Total markets: {total:,}")
report_lines.append(f"{'='*70}\n")

# category summary
report_lines.append("CATEGORY DISTRIBUTION")
report_lines.append("-" * 50)
for cat, cnt in cat_counts.items():
    pct = cnt / total * 100
    report_lines.append(f"  {cat:20s}  {cnt:>10,}  ({pct:5.1f}%)")
report_lines.append("")

# per-category detail
for c in TARGET_CATS:
    sub_df = cats[cats["category_llm"] == c]
    n = len(sub_df)
    report_lines.append(f"\n{'='*70}")
    report_lines.append(f"  {c.upper()} ({n:,} markets)")
    report_lines.append(f"{'='*70}")

    # subcategories
    report_lines.append("\n  Subcategories:")
    sub_counts = sub_df["subcategory_llm"].value_counts()
    for s, cnt in sub_counts.items():
        pct = cnt / n * 100
        report_lines.append(f"    {s:55s} {cnt:>6,} ({pct:4.1f}%)")

    # persons
    persons = []
    for raw in sub_df["ner_persons"]:
        try: persons.extend(json.loads(raw))
        except: pass
    pc = Counter(persons)
    report_lines.append(f"\n  Persons: {len(persons):,} mentions, {len(pc):,} unique")
    for name, cnt in pc.most_common(15):
        report_lines.append(f"    {name:40s} {cnt:>5,}")

    # companies
    companies = []
    for raw in sub_df["ner_companies"]:
        try: companies.extend(json.loads(raw))
        except: pass
    cc = Counter(companies)
    report_lines.append(f"\n  Companies: {len(companies):,} mentions, {len(cc):,} unique")
    for name, cnt in cc.most_common(15):
        report_lines.append(f"    {name:40s} {cnt:>5,}")

    # organizations
    orgs = []
    for raw in sub_df["ner_organizations"]:
        try: orgs.extend(json.loads(raw))
        except: pass
    oc = Counter(orgs)
    report_lines.append(f"\n  Organizations: {len(orgs):,} mentions, {len(oc):,} unique")
    for name, cnt in oc.most_common(15):
        report_lines.append(f"    {name:40s} {cnt:>5,}")

    # time trend
    sub_merged = merged[merged["category_llm"] == c]
    monthly = sub_merged.groupby("month").size()
    monthly = monthly[monthly.index >= "2024-01"].sort_index()
    report_lines.append(f"\n  Monthly trend (2024+):")
    for m, cnt in monthly.items():
        bar = "#" * (cnt // 50)
        report_lines.append(f"    {m}  {cnt:>5,}  {bar}")

report_txt = "\n".join(report_lines)
with open(os.path.join(DATA_OUTPUT, "category_report.txt"), "w", encoding="utf-8") as f:
    f.write(report_txt)
print("Saved: category_report.txt")

print(f"\nDone — all outputs in {DATA_OUTPUT}")
