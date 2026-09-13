# WiseMarket 🇨🇭

A smart shopping assistant that knows what's in your food, where it's cheapest, and what you can eat — in any Swiss language.

WiseMarket is a Swiss grocery intelligence platform: search or scan a product, compare its price across stores, get a deterministic breakdown of dietary/nutrition/allergen flags, and query a conversational AI assistant about your shopping.

---

## What it is

WiseMarket combines three things:

**Retrieval-grounded answers.** A user asks "what's the cheapest gluten-free pasta near me" → the app retrieves matching products from Postgres → passes that real data to an LLM → the LLM writes an answer grounded only in retrieved facts. No invented prices, no guessed availability.

**An agent layer.** The LLM detects intent, routes to the right deterministic tool (search, price compare, basket calculation), remembers user preferences and chat history, and adapts its responses per user.

**Deterministic core logic.** Price comparison, barcode scanning, PDF export, ingredient parsing, and the dietary decision engine are pure code — fast, explainable, not subject to hallucination. The LLM is used only where natural-language understanding is genuinely needed.

---

## Architecture

```
React (Vite) PWA
   │  fetch → VITE_API_URL
   ▼
FastAPI backend
   ├─ /analyze/{gtin}   → ontology matcher → decision engine → verdicts
   ├─ /products/*       → search, detail, nutrition, unified merged view
   ├─ /prices/*         → compare, history, latest
   ├─ /basket/*         → calculate, nutrition, PDF export
   ├─ /scan             → barcode → product + prices
   └─ /agent/*          → intent detection → DB tools → LLM (Groq, via LiteLLM)
   │
   ▼
Supabase Postgres
   public schema: products, product_prices, nutrition_facts,
                  store_price_snapshot, price_history, user_*
   unified_products / unified_product_members: cross-source merged
                  products (GTIN-exact matching, live — see below)
   analytics / events / etl schemas: reserved for future use
   │
   ▲ writes
ETL pipeline
   scraper_migros.py (Playwright)          — live, ~3,850 real products
   ingest_open_food_facts.py (REST)        — live, ~9,490 real products
   build_unified_products.py (GTIN merge)  — live, ~630 merged products
   Coop / Aldi / Lidl / Denner             — planned
```

**Frontend:** React 19 + Vite, mobile-first PWA. Pages: onboarding, home (search + deals), product detail, barcode scan, chat, basket (multi-store price comparison), profile, nearby stores (OpenStreetMap).

**Backend:** FastAPI. Routes grouped by domain, plus `/analyze/{gtin}` running the full ingredient-parsing → ontology-matching → decision-engine pipeline, returning ~30 dietary/nutrition/allergen verdicts with multilingual labels. The Product screen now calls this endpoint directly, surfacing real verdicts to users instead of raw, unprocessed tags.

**AI agent:** an intent → database-tool → LLM pipeline, using LiteLLM to route to Groq-hosted models.

**Database:** Supabase-hosted Postgres. Schema is version-controlled at `backend/schema/schema.sql`, with incremental changes tracked in `backend/schema/migrations/`.

---

## Cross-source product matching (new)

WiseMarket combines two real, independent data sources per product:

- **Migros** (scraped live) — real Swiss retail prices, pack sizes, images. Does **not** capture ingredients or allergens by itself.
- **Open Food Facts** (public database) — real ingredients, allergens, and nutrition facts for a global product catalog. Has **no** pricing data.

Where the same product exists in both sources (matched by GTIN, the barcode — the one identifier both databases share), a **unified record** is built combining the best of each:

| Data | Source | Labeled as |
|---|---|---|
| Name, price, image, category, source URL | Migros | `"migros"` (retailer) |
| Ingredients, allergens, nutrition | Open Food Facts | `"open_food_facts"` (third party) |
| Dietary/religious verdicts (halal, vegan, etc.) | Computed by the decision engine from the merged ingredients — never copied from either source | `"computed"` |

Every field in a unified record carries an explicit **source label**, so it's always clear whether a piece of information came from the retailer directly or from a third-party database — nothing is presented as verified when it hasn't been.

This currently covers **~630 real, verified product matches** (built via `backend/etl/build_unified_products.py`), and directly fixes a real gap: Migros' own scraped data has empty allergen/nutrition fields for essentially every product it captures, so matched products now get real, trustworthy safety data instead.

---

## Getting started

```bash
git clone <repo-url>
cd wisemarket
cp .env.example .env   # Supabase project URL/key, Groq API key
pip install -r requirements.txt
uvicorn backend.api.main:app --reload
```

```bash
cd frontend/wisemarket
npm install
npm run dev
```

See `.env.example` for every environment variable the app reads.

### Running the test suite

```bash
pytest -m "not integration" -q   # pure logic, no database needed — 71 tests
```

For the full suite including live-database integration tests, see [Testing](#testing) below.

---

## Database

Schema is version-controlled at `backend/schema/schema.sql`, with incremental changes in `backend/schema/migrations/`. Reproduce locally:

```bash
psql "<your-postgres-connection-string>" -f backend/schema/schema.sql
psql "<your-postgres-connection-string>" -f backend/schema/migrations/002_unified_merge_fields.sql
```

**Current status:** Row Level Security is enabled on every `public` table, but no policies are defined yet. The application currently runs with the Supabase `service_role` key, which bypasses RLS — a deliberate interim state until per-user authentication lands (see [Known limitations](#known-limitations)).

---

## Testing

- **Pure-logic tests** (`pytest -m "not integration"`) — ingredient parser, ontology matcher, decision engine. No database required.
- **Integration tests** (`pytest -m integration`) — real API endpoints against a live database. Require `SUPABASE_URL`/`SUPABASE_KEY` pointing at a seeded instance.

CI (`.github/workflows/ci.yml`) runs both tiers on every push/PR, spinning up a fresh local Supabase instance for the integration job — nothing touches production data.

---

## Known limitations

- **No RLS policies.** The app relies on `service_role` bypassing RLS entirely. Client-supplied `user_id` is trusted without verification — real per-user data isolation doesn't exist yet.
- **Migros scraper does not capture allergens, nutrition, or ingredients on its own.** Every Migros-scraped product has these fields empty by construction — the scraper's card/search API doesn't expose them. This is why the cross-source merge (above) exists; ~3,200 Migros products still have no Open Food Facts match and therefore no reliable safety data yet.
- **Two confirmed data-quality bugs in the Migros scraper's dietary tagging**, not yet fixed:
  - Non-food items (e.g. board games) can pass through and receive food-safety tags (halal/vegan/etc.) because the non-food filter is a small denylist rather than a positive food check.
  - Meat-substitute products are sometimes miscategorized as meat (via naive breadcrumb keyword matching), flipping vegetarian/halal flags backwards.
  - Both are mitigated for the ~630 unified-merge products (real ingredients replace name-guessing), but remain live for un-merged Migros products.
- **Pack-size capture is inconsistent across product categories.** A fix was applied to capture per-100g reference pricing and pack size directly from Migros' API; per-100g pricing now works reliably, but pack-size text is populated for some categories (e.g. meat) and not others (e.g. dairy) — needs further investigation.
- **A small number (~372) of Open Food Facts products were inadvertently removed** during a database cleanup pass and have not yet been re-ingested; the ingestion script currently always re-fetches the same fixed page range rather than resuming or targeting specific products.
- **`analytics`/`events`/`etl` schemas exist but are unused.** Reserved for a future analytics pipeline; no code currently reads or writes them.

---

## Roadmap

1. Expand the cross-source merge: increase Open Food Facts coverage (currently ~9,490 products, most without a Migros price match) and/or add a Migros per-product detail endpoint call for direct allergen/nutrition capture.
2. Fix the two remaining scraper tagging bugs (non-food pass-through, meat-substitute miscategorization) directly, for products that don't have a merge match.
3. Recover the ~372 accidentally-removed Open Food Facts products (expand ingestion page range or target by GTIN).
4. Add Supabase Auth, derive `user_id` from a verified JWT, and write real RLS policies (public read access on catalog tables, per-user policies on personal data tables).
5. Build out Coop/Aldi/Lidl/Denner scrapers, one store at a time, feeding the same unified-merge pipeline.
6. A lightweight validator on the AI agent's responses (drop stale prices, refuse answers without database evidence).
7. General cleanup and ongoing documentation upkeep.

---

## License

MIT License

Copyright (c) 2026 Abdulbari Soliman

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
