# ****************************************************
# step4_build_up_panel.py
# Input  : temp/key_market_company_full.parquet     (from step2_5_link_entities)
#           temp/markets_categories_entities_selected.parquet  (from step2_LLM_classification + step2_select_categories)
#           raw/markets.parquet                                (raw Polymarket)
#           raw/wrds/compustat_fm_qt.parquet                   (WRDS Compustat)
#           raw/wrds/confcall_fm_qt.parquet                    (WRDS Conference Calls)
#           raw/wrds/ceo_fm_yr.parquet                         (WRDS ExecuComp)
# Output : processed/panel_fm_qt_mkt.parquet
# Level  : firm x quarter x market
#          - treated rows: one row per (gvkey, year, quarter, market_id) within active window
#          - control rows: one row per (gvkey, year, quarter) for unmatched firms
# ****************************************************

import os
import polars as pl

from config import DATA_TEMP, DATA_RAW, DATA_RAW_WRDS, DATA_PROCESSED

os.makedirs(DATA_PROCESSED, exist_ok=True)

# ==============================================================
#  1. Load key linkage and market data
# ==============================================================

key = pl.read_parquet(os.path.join(DATA_TEMP, "key_market_company_full.parquet"))
SAMPLE_CUTOFF = pl.datetime(2026, 1, 1, time_zone="UTC")

# raw column -> snake_case
RAW_TO_SNAKE = {
    "id": "market_id",
    "createdAt": "created_at",
    "closedTime": "closed_time",
    "endDate": "end_date",
    "startDate": "start_date",
    "volumeNum": "volume_num",
    "volume24hr": "volume_24hr",
    "volume1wk": "volume_1wk",
    "volume1mo": "volume_1mo",
    "volume1yr": "volume_1yr",
    "liquidityNum": "liquidity_num",
    "lastTradePrice": "last_trade_price",
    "bestBid": "best_bid",
    "bestAsk": "best_ask",
    "oneDayPriceChange": "one_day_price_change",
    "oneWeekPriceChange": "one_week_price_change",
    "oneMonthPriceChange": "one_month_price_change",
    "oneYearPriceChange": "one_year_price_change",
    "outcomePrices": "outcome_prices",
    "resolutionSource": "resolution_source",
    "resolvedBy": "resolved_by",
    "negRisk": "neg_risk",
}

MARKET_COLS = list(RAW_TO_SNAKE.keys()) + [
    "question", "slug", "description",
    "closed", "active", "archived", "restricted", "approved", "new", "featured",
    "competitive", "spread", "outcomes",
]

markets = (
    pl.read_parquet(os.path.join(DATA_RAW, "markets.parquet"), columns=MARKET_COLS)
    .rename(RAW_TO_SNAKE)
    .with_columns(
        pl.col("created_at").str.to_datetime(time_zone="UTC", strict=False),
        pl.col("closed_time").fill_null("2026-01-01 00:00:00+00:00")
            .str.to_datetime(time_zone="UTC", strict=False),
        pl.col("end_date").str.to_datetime(time_zone="UTC", strict=False),
        pl.col("start_date").str.to_datetime(time_zone="UTC", strict=False),
    )
    .with_columns(
        pl.when(pl.col("closed_time") < SAMPLE_CUTOFF)
        .then(pl.lit(1)).otherwise(pl.lit(0))
        .alias("i_resolved"),
        ((pl.col("closed_time") - pl.col("created_at")).dt.total_seconds() / 86400)
            .alias("market_duration_days"),
    )
    .filter(pl.col("created_at") >= pl.datetime(2020, 1, 1, time_zone="UTC"))
)

# attach LLM categories / NER entities
mkt_cats = pl.read_parquet(os.path.join(DATA_TEMP, "markets_categories_entities_selected.parquet"),
                           columns=["id", "category_llm", "subcategory_llm",
                                    "ner_persons", "ner_companies", "ner_organizations"])
markets = markets.join(mkt_cats.rename({"id": "market_id"}), on="market_id", how="left")

print(f"Key: {key.height:,} rows ({key['gvkey'].n_unique():,} firms)")
print(f"Markets (post-2020): {markets.height:,} | columns: {markets.width}")

# ==============================================================
#  2. Join key to markets -> one row per (firm, market)
# ==============================================================

fm = key.join(markets, on="market_id", how="inner")
print(f"Firm-market pairs: {fm.height:,}")

# ==============================================================
#  3. Expand to firm-quarter-market: keep only quarters where
#     the market was active (created_at <= q_end AND closed_time >= q_start)
# ==============================================================

quarters = pl.DataFrame({
    "year": [y for y in range(2020, 2026) for _ in range(4)],
    "quarter": [q for _ in range(2020, 2026) for q in range(1, 5)],
})

from datetime import datetime, timezone

q_bounds = []
for y in range(2020, 2026):
    for q in range(1, 5):
        q_start = datetime(y, (q - 1) * 3 + 1, 1, tzinfo=timezone.utc)
        q_end_month = q * 3
        if q_end_month == 12:
            q_end = datetime(y + 1, 1, 1, tzinfo=timezone.utc)
        else:
            q_end = datetime(y, q_end_month + 1, 1, tzinfo=timezone.utc)
        q_bounds.append({"year": y, "quarter": q, "q_start": q_start, "q_end": q_end})

qb = pl.DataFrame(q_bounds).with_columns(
    pl.col("q_start").cast(pl.Datetime("us", "UTC")),
    pl.col("q_end").cast(pl.Datetime("us", "UTC")),
)

panel = (
    fm.join(qb, how="cross")
    .filter(
        (pl.col("created_at") < pl.col("q_end")) &
        (pl.col("closed_time") >= pl.col("q_start"))
    )
    .drop("q_start", "q_end")
    .with_columns(
        (pl.col("volume_num").fill_null(0) + 1).log().alias("ln_volume"),
    )
)

# ==============================================================
#  3b. Add control group: Compustat firms NEVER matched to any market
# ==============================================================

all_firms = (
    pl.read_parquet(os.path.join(DATA_RAW_WRDS, "compustat_fm_qt.parquet"),
                    columns=["gvkey", "fyearq"])
    .filter(pl.col("fyearq").is_between(2020, 2025))
    .select("gvkey").unique()
)

treated_firms = fm.select("gvkey").unique()
control_firms = all_firms.join(treated_firms, on="gvkey", how="anti")

control_rows = (
    control_firms.join(quarters, how="cross")
    .with_columns(pl.lit(0).cast(pl.Int8).alias("i_treated_firm"))
)

panel = panel.with_columns(pl.lit(1).cast(pl.Int8).alias("i_treated_firm"))

# concat — diagonal_relaxed fills missing market cols with nulls in controls
panel = pl.concat([panel, control_rows], how="diagonal_relaxed")

print(f"\nPanel (firm x quarter x market + controls): {panel.height:,} rows")
print(f"  Treated (market-level): {panel.filter(pl.col('market_id').is_not_null()).height:,}")
print(f"  Control rows: {control_rows.height:,}")
print(f"  Unique firms: {panel['gvkey'].n_unique():,}")

# ==============================================================
#  4. Merge Compustat controls (firm-quarter)
# ==============================================================

ctrl_cols = ["gvkey", "fyearq", "fqtr", "conm",
             "atq", "saleq", "niq", "mkvaltq",
             "size", "leverage", "roa", "mtb", "sale_growth",
             "loss", "rd_int", "cfo", "tangibility"]

compustat_ctrl = (
    pl.read_parquet(os.path.join(DATA_RAW_WRDS, "compustat_fm_qt.parquet"),
                    columns=ctrl_cols)
    .rename({"fyearq": "year", "fqtr": "quarter"})
    .unique(subset=["gvkey", "year", "quarter"], keep="first")
)

panel = panel.join(compustat_ctrl, on=["gvkey", "year", "quarter"], how="left")
print(f"Panel after compustat merge: {panel.shape}")

# ==============================================================
#  5. Merge Conference Call data (voluntary disclosure)
# ==============================================================

confcall = (
    pl.read_parquet(os.path.join(DATA_RAW_WRDS, "confcall_fm_qt.parquet"))
    .with_columns(
        pl.col("year").cast(pl.Int64),
        pl.col("quarter").cast(pl.Int64),
    )
)

panel = (
    panel.join(confcall, on=["gvkey", "year", "quarter"], how="left")
    .with_columns(
        pl.col("n_conf_calls").fill_null(0),
        pl.col("n_earnings_call").fill_null(0),
    )
)
print(f"Panel after confcall merge: {panel.shape}")

# ==============================================================
#  6. Merge CEO characteristics (annual -> quarter)
# ==============================================================

ceo_cols = ["gvkey", "year", "exec_fullname", "gender", "age", "tenure_years",
            "salary", "bonus", "tdc1"]

ceo_sel = (
    pl.read_parquet(os.path.join(DATA_RAW_WRDS, "ceo_fm_yr.parquet"), columns=ceo_cols)
    .with_columns(pl.col("year").cast(pl.Int64))
    .rename({"exec_fullname": "ceo_name_wrds"})
    .unique(subset=["gvkey", "year"], keep="first")
)

panel = panel.join(ceo_sel, on=["gvkey", "year"], how="left")
print(f"Panel after CEO merge: {panel.shape}")

# ==============================================================
#  7. Final cleaning
# ==============================================================

panel = (
    panel
    .with_columns(
        (pl.col("year").cast(pl.Utf8) + "Q" + pl.col("quarter").cast(pl.Utf8)).alias("yearqtr"),
    )
    .sort("gvkey", "year", "quarter", "market_id")
)

# column order
col_order = (
    # ---- identifiers ----
    ["gvkey", "year", "quarter", "yearqtr", "conm", "i_treated_firm",
     "market_id", "slug", "question", "description"]
    # ---- entity-link info ----
    + ["match_tier", "mentioned_ceo"]
    # ---- market timing / status ----
    + ["created_at", "closed_time", "end_date", "start_date", "market_duration_days",
       "i_resolved", "closed", "active", "archived", "restricted", "approved",
       "new", "featured", "neg_risk"]
    # ---- LLM category / NER ----
    + ["category_llm", "subcategory_llm",
       "ner_persons", "ner_companies", "ner_organizations"]
    # ---- market volume / liquidity ----
    + ["volume_num", "ln_volume", "volume_24hr", "volume_1wk", "volume_1mo", "volume_1yr",
       "liquidity_num", "competitive", "spread"]
    # ---- market price / outcomes ----
    + ["last_trade_price", "best_bid", "best_ask",
       "one_day_price_change", "one_week_price_change",
       "one_month_price_change", "one_year_price_change",
       "outcomes", "outcome_prices",
       "resolution_source", "resolved_by"]
    # ---- firm-quarter financials (Compustat) ----
    + ["size", "leverage", "roa", "mtb", "sale_growth",
       "loss", "rd_int", "cfo", "tangibility",
       "atq", "saleq", "niq", "mkvaltq"]
    # ---- firm-quarter voluntary disclosure ----
    + ["n_conf_calls", "n_earnings_call"]
    # ---- CEO (annual, ExecuComp) ----
    + ["ceo_name_wrds", "gender", "age", "tenure_years", "salary", "bonus", "tdc1"]
)
col_order = [c for c in col_order if c in panel.columns]
extra = [c for c in panel.columns if c not in col_order]
panel = panel.select(col_order + extra)

print(f"\nFinal panel: {panel.height:,} rows x {panel.width} cols")
print(f"  {panel['gvkey'].n_unique():,} firms, {panel['market_id'].n_unique():,} markets, {panel['yearqtr'].n_unique()} quarters")
print(f"  Resolved markets: {panel['i_resolved'].sum():,} / {panel.height:,}")
print(f"  Compustat coverage: {panel['atq'].is_not_null().sum():,} rows")
print(f"  CEO coverage: {panel['ceo_name_wrds'].is_not_null().sum():,} rows")

panel.write_parquet(os.path.join(DATA_PROCESSED, "panel_fm_qt_mkt.parquet"))
print(f"\nSaved: data/processed/panel_fm_qt_mkt.parquet")
