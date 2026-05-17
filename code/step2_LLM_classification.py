import os
import json
import re
import polars as pl
from vllm import LLM, SamplingParams

from config import DATA_INPUT, DATA_TEMP

MODEL_ID   = "RedHatAI/Llama-4-Scout-17B-16E-Instruct-quantized.w4a16"
DATA_PATH  = DATA_INPUT / "markets.parquet"
OUT_PATH   = DATA_TEMP / "markets_categories_entities.parquet"
CHUNK_SIZE = 5_000
NUM_GPUS   = int(os.environ.get("NUM_GPUS", 1))

VALID_CATEGORIES = {
    "politics", "geopolitics", "sports", "crypto", "tech",
    "economics", "business", "culture", "science", "weather", "commodities",
}

SYSTEM_PROMPT = """\
You are a prediction-market classifier. Given a market question and description, \
output ONLY a JSON object — no explanation, no markdown, no extra text.

JSON schema (use exactly these keys):
{
  "category": "<see list below>",
  "subcategory": "<see list below, or 'other' if none fit>",
  "entities": {
    "persons": ["<full name>"],
    "companies": ["<company / corp, e.g. Apple, Tesla, OpenAI>"],
    "organizations": ["<non-company org, e.g. UN, FBI, Lakers, NATO>"],
    "locations": ["<place name>"]
  }
}

Categories and their subcategories:
- politics: Presidential & Congressional elections | Global elections | Policy & legislation outcomes | Domestic political events | other
- geopolitics: Middle East conflicts | Russia & Ukraine | Iran & sanctions | International diplomacy | other
- sports: NFL / American Football | NBA / Basketball | Soccer / Football | MLB / Baseball | NHL / Hockey | Olympics | Esports / Chess / Poker | other
- crypto: Bitcoin (BTC) price | Ethereum (ETH) price | Altcoins & DeFi | NFTs | Crypto regulation | other
- tech: AI benchmarks & model releases | Self-driving / autonomous vehicles | Space missions | Drug & FDA approvals | Tech company acquisitions & leadership | other
- economics: GDP & inflation | Federal Reserve & interest rates | Stock market indices | Foreign exchange (FX) | other
- business: Corporate earnings | Mergers & acquisitions | Company leadership changes | IPOs & fundraising | other
- culture: Oscars & film awards | Box office gross | Music & TV awards | Celebrity events | Visual art & auctions | other
- science: Epidemics & public health | Medical research & drug approvals | Academic & Nobel prizes | other
- weather: Daily / monthly temperature by city | Hurricanes & storms | Natural disasters | other
- commodities: Crude oil price | Gold & silver | Agricultural commodities | other

Rules:
- category should be exactly one of the 11 listed values and "other" if none fit.
- subcategory should match one of the options listed for that category or use "other".
- entities: only names explicitly mentioned in the text; use [] if none.
- Output raw JSON only. No backticks, no comments, no extra fields.\
"""

_JSON_RE = re.compile(r'\{.*\}', re.DOTALL)


def parse_output(text: str, row_id) -> dict:
    m = _JSON_RE.search(text)
    if m:
        try:
            obj  = json.loads(m.group())
            cat  = obj.get("category", "").strip().lower().replace(" ", "_")
            ents = obj.get("entities", {})
            return {
                "id":                row_id,
                "category_llm":      cat if cat in VALID_CATEGORIES else "unknown",
                "subcategory_llm":   str(obj.get("subcategory", "")).strip()[:80],
                "ner_persons":       json.dumps(ents.get("persons",       []), ensure_ascii=False),
                "ner_companies":     json.dumps(ents.get("companies",     []), ensure_ascii=False),
                "ner_organizations": json.dumps(ents.get("organizations", []), ensure_ascii=False),
                "ner_locations":     json.dumps(ents.get("locations",     []), ensure_ascii=False),
                "llm_raw":           text[:400],
            }
        except json.JSONDecodeError:
            pass
    return {
        "id": row_id, "category_llm": "parse_error", "subcategory_llm": "",
        "ner_persons": "[]", "ner_companies": "[]", "ner_organizations": "[]", "ner_locations": "[]",
        "llm_raw": text[:400],
    }


def main():
    os.environ["HF_HOME"] = "/gpfs/home/yw984/.cache/huggingface"

    df = pl.read_parquet(DATA_PATH).select(["id", "question", "description"])
    total      = len(df)
    num_chunks = (total + CHUNK_SIZE - 1) // CHUNK_SIZE
    print(f"Loaded {total:,} rows → {num_chunks} chunks")

    llm = LLM(model=MODEL_ID, tensor_parallel_size=NUM_GPUS,
               max_model_len=1024, gpu_memory_utilization=0.92)
    sampling_params = SamplingParams(temperature=0.0, max_tokens=220)
    print("Model ready.\n")

    records = []
    for chunk_idx in range(num_chunks):
        start = chunk_idx * CHUNK_SIZE
        chunk = df.slice(start, min(CHUNK_SIZE, total - start))

        messages_batch = [
            [{"role": "system", "content": SYSTEM_PROMPT},
             {"role": "user",   "content": f"Question: {q or ''}\nDescription: {(d or '')[:800]}"}]
            for q, d in zip(chunk["question"].to_list(), chunk["description"].to_list())
        ]

        print(f"  [{chunk_idx+1}/{num_chunks}] rows {start:,}–{start+len(chunk):,} …", flush=True)
        outputs = llm.chat(messages_batch, sampling_params)

        records += [
            parse_output(out.outputs[0].text.strip(), chunk["id"][i])
            for i, out in enumerate(outputs)
        ]

    pl.DataFrame(records).write_parquet(OUT_PATH)
    print(f"Done — {len(records):,} rows → {OUT_PATH}")


if __name__ == "__main__":
    main()
