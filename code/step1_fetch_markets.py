"""
Fetch all markets from https://gamma-api.polymarket.com/markets and save as markets.parquet.
Paginates with limit=500 until the API returns fewer than 500 results.
"""

import time

import polars as pl
import requests

from config import DATA_RAW

API_URL = "https://gamma-api.polymarket.com/markets"
PAGE_SIZE = 500
OUT = DATA_RAW / "markets.parquet"


def fetch_all_markets() -> list[dict]:
    session = requests.Session()
    all_markets: list[dict] = []
    offset = 0

    while True:
        resp = session.get(
            API_URL,
            params={"limit": PAGE_SIZE, "offset": offset},
            timeout=30,
        )
        resp.raise_for_status()
        page = resp.json()

        if not page:
            break

        all_markets.extend(page)
        print(f"  fetched {len(all_markets):,} markets so far (offset={offset})", end="\r")

        if len(page) < PAGE_SIZE:
            break

        offset += PAGE_SIZE
        time.sleep(0.1)  # be polite

    print()
    return all_markets


def main():
    print("Fetching markets from gamma-api.polymarket.com...")
    markets = fetch_all_markets()
    print(f"Total markets fetched: {len(markets):,}")

    # Normalise list/dict fields to strings so parquet schema stays flat
    for m in markets:
        for key in list(m.keys()):
            val = m[key]
            if isinstance(val, (list, dict)):
                import json
                m[key] = json.dumps(val)

    df = pl.from_dicts(markets, infer_schema_length=None)
    df.write_parquet(OUT, compression="zstd")
    print(f"Saved {len(df):,} rows, {len(df.columns)} columns -> {OUT.name} ({OUT.stat().st_size / 1e6:.1f} MB)")
    print("\nColumns:", df.columns)


if __name__ == "__main__":
    main()


"""
NER — extract places, people, orgs from the `question` column.
Requires: pip install spacy && python -m spacy download en_core_web_sm
"""

import re

import polars as pl
import spacy
import torch

# ── Constants ─────────────────────────────────────────────────────────────────

DATA_PATH  = DATA_RAW / "markets.parquet"
BATCH_SIZE = 512

LABELS = {
    "PERSON": "people",
    "ORG":    "companies",
    "GPE":    "countries_cities",
    "LOC":    "states_regions",
}

TICKER_RE = re.compile(r'\$([A-Z]{1,5})\b|\b([A-Z]{2,5})\s+stock\b')

# ── Load ──────────────────────────────────────────────────────────────────────

print(torch.cuda.is_available())
spacy.require_gpu()
nlp = spacy.load("en_core_web_trf", enable=["transformer", "ner"])

market       = pl.read_parquet(DATA_PATH)
descriptions = market["description"].fill_null("").to_list()
print(f"Total docs: {len(descriptions):,}")

# ── NER ───────────────────────────────────────────────────────────────────────

cols = {v: [] for v in [*LABELS.values(), "stock_codes"]}

for i, doc in enumerate(nlp.pipe(descriptions, batch_size=BATCH_SIZE)):
    row = {v: set() for v in cols}
    for ent in doc.ents:
        if col := LABELS.get(ent.label_):
            row[col].add(ent.text.strip())
    for m in TICKER_RE.finditer(doc.text):
        row["stock_codes"].add((m.group(1) or m.group(2)).strip())
    for v in cols:
        cols[v].append(sorted(row[v]))

    if i % 10_000 == 0:
        print(f"  {i:>7,} / {len(descriptions):,}")

# ── Save ──────────────────────────────────────────────────────────────────────

market_ner = market.with_columns([pl.Series(k, v) for k, v in cols.items()])
market_ner.write_parquet(DATA_PATH.with_stem(DATA_PATH.stem + "_ner"))
print("Saved.")




import requests
r = requests.get('https://gamma-api.polymarket.com/markets', params={'limit':1, 'offset':0})
print('No params:', r.json()[0].get('createdAt'))

r = requests.get('https://gamma-api.polymarket.com/markets', params={'limit':1, 'offset':0, 'order':'createdAt', 'ascending':'true'})
print('Ascending:', r.json()[0].get('createdAt'))