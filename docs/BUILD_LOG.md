# WiseMarket — Technical Steps Documentation


This document records the technical build steps completed so far in WiseMarket, including:

* what was built
* why it was needed
* where the code/files live
* how each step was tested
* what remains next

This is a **technical process document**, not a README.

---

# Step 1 — Ontology category design

## What was done

A multilingual ontology system was designed for Swiss grocery and retail product intelligence.

Each ontology CSV represents one semantic category, for example:

* allergens
* pork
* alcohol
* animal_products
* vegan_markers
* vegetarian_markers
* sugar_synonyms
* promotion_terms
* regional_labels
* fish_synonyms
* lactose_free_labels

The ontology supports:

* English
* German
* French
* Italian

## Why

The ontology is the rule foundation of the project. It allows the app to interpret product ingredients and labels in a deterministic and explainable way.

## Output

66 ontology CSV files under:

```text
data/ontology/
```

---

# Step 2 — Ontology generator

## What was done

A generator script was created to generate and rewrite ontology CSV files consistently.

## File

```text
data/ontology/tools/generate_ontology.py
```

## Why

The generator avoids manual CSV inconsistency and makes ontology creation reproducible.

## Run command

```bash
python data/ontology/tools/generate_ontology.py
```

---

# Step 3 — Ontology validation

## What was done

The ontology folder contents were checked and validated using shell commands such as:

```bash
wc -l data/ontology/*.csv
```

## Why

This verified that:

* all ontology files exist
* they are not empty
* row counts look reasonable
* the generator produced content

## Result

The ontology set reached 66 CSV categories with populated rows.

---

# Step 4 — Ontology loader / runtime memory

## What was done

A loader was created to read ontology CSVs into Python memory.

## File

```text
backend/normalizer/ontology_loader.py
```

## Why

The ontology must be available in runtime memory for fast matching.

## Current function

```python
load_ontology()
```

---

# Step 5 — Supabase integration

## What was done

Supabase was chosen as the main backend database layer for Swiss-Basket-AI.

It is used for:

* product storage
* price history
* normalized ingredient storage
* runtime API fetching
* user memory
* feedback / ratings
* authentication (future)

## Why Supabase

Supabase provides:

* managed PostgreSQL
* simple setup
* SQL support
* auth support
* storage support
* vector search support (future)

---

# Step 6 — Database schema design and deployment

## What was done

Two complete PostgreSQL schemas were designed, reviewed, and deployed to Supabase.

### Schema 1 — Products + ETL + Price Calculator

**File:** `database/schema_1_v2_1_migration_safe.sql`

**Schemas created:**

* `public` — live app tables
* `etl` — scraper pipeline tables
* `archive` — legacy read-only tables

**Key tables:**

| Table | Purpose |
|---|---|
| `products` | Master product catalogue (GTIN + store keyed) |
| `barcode_aliases` | Normalises raw barcodes to GTIN |
| `unified_products` | Cross-store canonical product records |
| `unified_product_members` | Maps store products to canonical records |
| `nutrition_facts` | Master nutrition data (per 100g + per serving) |
| `product_prices` | Current prices with auto-computed price_per_100g |
| `price_history` | One price snapshot per product/store/day |
| `store_price_snapshot` | Cross-store JSONB comparison per GTIN |
| `ontology_versions` | Versioning for ontology rule changes |
| `ontology_current` | Single-row table enforcing one active version |
| `user_preferences` | Dietary flags + store prefs + GDPR consent |
| `user_scans` | Every barcode scan per user |
| `user_searches` | Every search query per user |
| `user_saved_products` | Bookmarked products |
| `user_feedback` | Verdict dispute reports |
| `user_lists` | Shopping lists |
| `user_list_items` | Items inside shopping lists |
| `user_chat_history` | Conversation history for LLM context |
| `consent_audit_log` | GDPR Article 7 consent proof |
| `data_access_log` | GDPR Article 30 access log |
| `data_deletion_log` | GDPR right to erasure tracking |
| `privacy_policy_versions` | Versioned privacy policy with 4-language summaries |
| `agent_execution_log` | Every request through the agent pipeline |
| `etl.scraper_sources` | Registry of stores + scrape config |
| `etl.scraper_jobs` | Every scraper run with counters |
| `etl.scraper_change_log` | What changed in each scrape run |
| `etl.scrape_failures` | Detailed scraper error tracking |
| `etl.staging_products` | Raw scraper output before validation |
| `etl.ontology_improvement_queue` | User/system signals for ontology updates |

**Key triggers:**

* `fn_compute_unit_prices` — auto-computes `price_per_100g` on every price insert
* `fn_append_price_history` — auto-writes to `price_history` on every price write
* `fn_sync_nutrition_cache` — syncs `nutrition_facts` changes to `products.nutrition_cache`
* `fn_clear_nutrition_cache` — nulls cache on nutrition delete
* `fn_validate_price_product_ref` — enforces gtin/store consistency on prices
* `fn_sync_unified_master` — keeps `master_product_id` in sync with `is_master` flag
* `fn_rebuild_price_snapshot` — callable function to rebuild cross-store comparison

**Price calculator views:**

* `v_price_comparison` — cross-store comparison using latest snapshot
* `v_price_history_stats` — rolling 28-day average, direction signal, all-time low/high
* `v_best_value` — ranks stores by price_per_100g, powers best-value badge
* `v_basket_prices` — basket calculator feed with dietary tag filtering
* `v_active_promotions` — current promotions sorted by discount

**ETL views:**

* `v_ontology_priority` — pending ontology improvements by urgency
* `v_scraper_health` — live scraper status per store

### Schema 2 — Analytics + Events

**File:** `database/schema_02_analytics_events.sql`

**Schemas created:**

* `events` — raw append-only event stream
* `analytics` — nightly aggregated tables

**Design principle:** App writes to `events.*` only. Analytics worker reads events and writes aggregates. Views read from aggregates only.

**Event tables (12):**

* `events.user_events`
* `events.session_events`
* `events.scan_events`
* `events.search_events`
* `events.chat_events`
* `events.product_events`
* `events.feedback_events`
* `events.price_events`
* `events.feature_events`
* `events.error_events`
* `events.api_events`
* `events.allergen_alert_events`

**Analytics aggregate tables (17):**

* `analytics.user_growth`
* `analytics.retention_cohorts`
* `analytics.product_performance`
* `analytics.session_quality`
* `analytics.feature_popularity`
* `analytics.search_patterns`
* `analytics.category_analytics`
* `analytics.verdict_analytics`
* `analytics.dietary_trends`
* `analytics.price_analytics`
* `analytics.swiss_regional`
* `analytics.llm_quality`
* `analytics.allergen_risk`
* `analytics.verdict_disputes`
* `analytics.api_usage`
* `analytics.b2b_report_access`
* `analytics.app_behaviour`
* `analytics.rebuild_log`

**Smart views (12):**

* `v_user_growth`
* `v_feature_popularity`
* `v_session_quality`
* `v_product_popularity`
* `v_app_mode_usage`
* `v_disputed_verdicts`
* `v_allergen_risk`
* `v_llm_quality`
* `v_swiss_dietary_demand`
* `v_ontology_priority`
* `v_price_intelligence`
* `v_error_health`
* `v_api_performance`

### Also deployed

**File:** `database/patch_001_image_fields.sql`

Added to `products`:

* `image_source` — enum: `retailer_url`, `open_food_facts`, `gs1`, `internal`
* `image_url_verified_at` — last time URL returned 200
* `image_url_is_dead` — flagged when URL goes 404

**Legal note:** Images are never downloaded or stored. Only URLs are stored. Copyright belongs to retailers.

---

# Step 7 — ETL ingestion pipeline

## What was done

A Python ETL pipeline was created to ingest:

* ontology-aware product data
* product CSVs by store
* price CSVs by store

into Supabase.

## Main ETL files

```text
backend/etl/split_by_store.py
backend/etl/supabase_ingest.py
```

## Result

ETL completed successfully. Product analysis data became queryable from Supabase.

---

# Step 8 — Seed data

## What was done

Realistic Swiss supermarket seed data was created and deployed to Supabase.

**File:** `database/seed_data.sql`

## What was seeded

| Table | Rows |
|---|---|
| `products` | 51 |
| `product_prices` | 51 |
| `nutrition_facts` | 51 |
| `unified_products` | 23 |
| `store_price_snapshot` | 23 |
| `user_preferences` | 3 |
| `user_scans` | 8 |
| `user_saved_products` | 8 |
| `user_lists` | 3 |
| `user_list_items` | 12 |

## Stores covered

* Migros
* Coop
* Aldi
* Lidl

## Categories covered

Dairy, dairy alternative, meat, fish, bakery, fresh produce, pantry, beverages, snacks, frozen, plant protein

## Dietary tags

`halal`, `vegan`, `vegetarian`, `gluten_free`, `lactose_free`, `organic`, `high_protein`, `low_sugar`, `dairy_free`, `nut_free`

## Promotions

4 active promotions with discount_pct, promotion_label, promotion_ends

## Price history

30 days of price snapshots on key products (milk, chicken, olive oil, pasta) showing price movements

## Verification query

```sql
SELECT
    (SELECT COUNT(*) FROM products)             AS products,
    (SELECT COUNT(*) FROM product_prices)       AS prices,
    (SELECT COUNT(*) FROM nutrition_facts)      AS nutrition,
    (SELECT COUNT(*) FROM unified_products)     AS unified,
    (SELECT COUNT(*) FROM store_price_snapshot) AS snapshots;
```

---

# Step 9 — Repository structure cleanup

## What was done

Repository was reorganised before building the API.

**Removed:**

* `..env.swp` — vim swap file
* `.generate_master_ontology.py.swp` — vim swap file
* `main` — empty root file
* `venv/` — duplicate virtualenv (`.venv/` is correct)

**Added:**

* `backend/api/routes/` — route modules
* `backend/models/` — Pydantic schemas
* `database/` — all SQL files
* `requirements.txt`
* `Dockerfile`
* `.dockerignore`

**Virtualenv fixed:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn supabase python-dotenv pydantic slowapi sentry-sdk pytest httpx reportlab qrcode pillow
```

---

# Step 10 — Store configuration

## File

```text
backend/config/stores.py
```

## Current stores

| Store | Public | Scrape type |
|---|---|---|
| migros | ✅ | playwright |
| coop | ✅ | playwright |
| aldi | ✅ | httpx_bs4 |
| lidl | ✅ | httpx_bs4 |
| denner | ❌ | httpx_bs4 (pending) |

---

# Step 11 — Ingredient parser

## File

```text
backend/services/ingredient_parser.py
```

## Features

* lowercase normalisation
* split outside parentheses
* flatten nested ingredients
* remove percentages and units
* normalise E-number variants (E 322 → e322)
* preserve order
* deduplicate

## Example

Input:
```text
Milk chocolate (sugar, cocoa butter, milk powder, E 322), hazelnuts (10%), salt.
```

Output:
```python
['milk chocolate', 'hazelnuts', 'salt', 'sugar', 'cocoa butter', 'milk powder', 'e322']
```

---

# Step 12 — Ontology router

## File

```text
backend/services/ontology_router.py
```

## Universal groups (always checked)

* allergens
* animal_products
* promotion_terms
* price_unit_aliases
* sugar_synonyms
* salt_synonyms

## Category routing (v2 — expanded)

| Category | Extra groups |
|---|---|
| dairy | lactose_free_labels, vegan_markers, vegetarian_markers, bio_labels, organic_variants, animal_welfare |
| dairy_alternative | lactose_free_labels, vegan_markers, vegetarian_markers |
| meat | meat, pork, animal_welfare, bio_labels, organic_variants |
| poultry | meat, pork, animal_welfare |
| fish | fish_synonyms, shellfish_synonyms, histamine_triggers, sulphite_markers |
| seafood | fish_synonyms, shellfish_synonyms, histamine_triggers, sulphite_markers |
| snacks | nut_synonyms, superfood_markers, palm_oil, caffeine, artificial_sweeteners |
| chocolate | vegan_markers, palm_oil, fairtrade_labels, superfood_markers |
| bakery | vegan_markers, vegetarian_markers, gluten_free_labels, coeliac_triggers, egg_synonyms, alcohol |
| beverages | caffeine, sugar_synonyms, artificial_sweeteners, alcohol, vegan_markers |
| pantry | vegan_markers, vegetarian_markers, gluten_free_labels, coeliac_triggers, bio_labels, fairtrade_labels |
| frozen | vegan_markers, vegetarian_markers, gluten_free_labels |
| fresh_produce | vegan_markers, bio_labels, organic_variants, regional_labels, fairtrade_labels, sustainability_labels |
| plant_protein | vegan_markers, high_protein_markers, protein_vegan, soy_synonyms |
| sports nutrition | sports_nutrition_markers, high_protein_markers, protein_animal, protein_vegan, keto_markers |
| baby | child_friendly_markers, allergens, lactose_free_labels, vitamin_markers, mineral_markers |

---

# Step 13 — Ontology matcher

## File

```text
backend/services/ontology_matcher.py
```

## How it works

Builds an in-memory index from ontology CSVs. For each routed group, checks parsed ingredient tokens against the index. Returns matched terms per group.

## Output example

```python
{
    "allergens": ["milk"],
    "animal_products": ["milk powder"]
}
```

---

# Step 14 — Decision engine (v2)

## File

```text
backend/services/decision_engine.py
```

## Verdict categories

**Core:**
`halal`, `vegan`, `vegan_likely`, `vegetarian`, `allergen_warning`, `regional`

**Dietary:**
`is_gluten_free`, `is_lactose_free`, `is_keto`, `is_low_sugar`, `is_low_fat`, `is_high_protein`, `is_high_fiber`, `is_diabetic_friendly`

**Labels:**
`is_bio`, `is_fairtrade`, `is_sustainable`, `is_kids_friendly`, `is_sports`, `is_animal_welfare`

**Warnings:**
`has_caffeine`, `has_palm_oil`, `has_histamine_risk`, `has_sulphites`

**Nutrition:**
`has_vitamins`, `has_minerals`, `has_antioxidants`, `has_superfoods`, `has_probiotics`

**Packages:**
Grouped multilingual user-facing labels with id, label (4 languages), icon, confidence (high/medium)

## Key rules

* `pork` or `alcohol` hit → `halal = False`
* `animal_products` hit → `vegan = False`, `vegan_likely = False`
* `vegan_likely = True` only when no animal hits AND no vegan marker
* `vegan = True` only when vegan marker present AND no animal hits
* `gluten_free_labels` hit + `coeliac_triggers` hit → `is_gluten_free = False` (trigger overrides label)
* `vegan` package shown → `vegan_likely` package suppressed
* `vegan_likely` always shown with `confidence: medium`

## 30 package labels in 4 languages

halal, vegan, vegan_likely, vegetarian, gluten_free, lactose_free, keto, low_sugar, low_fat, diabetic_friendly, high_protein, high_fiber, vitamins, minerals, antioxidants, superfoods, probiotics, bio, fairtrade, sustainable, animal_welfare, regional, sports, kids, allergen_warning, caffeine, palm_oil, histamine_risk, sulphites

---

# Step 15 — API database connector

## File

```text
backend/api/db.py
```

## Environment variables required

```text
SUPABASE_URL
SUPABASE_KEY
```

---

# Step 16 — FastAPI application (v2)

## File

```text
backend/api/main.py
```

## Architecture

* Lifespan loads ontology + all services once at startup
* Rate limiting via `slowapi` (60 req/min public)
* Sentry error tracking
* Admin routes protected by `X-Admin-Key` header (constant-time comparison)
* Route modules imported and registered via `include_router`

---

# Step 17 — API endpoints

## Core endpoints

### `GET /`
Health ping. Returns `{"message": "WiseMarket API v2 is running"}`

### `GET /health`
Returns service status, version, public stores list.

### `GET /analyze/{gtin}`
Full ontology pipeline analysis. Returns verdicts, packages, price, ingredients.

### `GET /admin/stats` (requires X-Admin-Key header)
Store config + service status.

### `GET /admin/health` (requires X-Admin-Key header)
Detailed health including Sentry and key status.

## Products routes — `GET /products/...`

### `GET /products/search`

Query params:
* `q` — name search
* `store` — filter by store
* `category` — filter by category
* `halal`, `vegan`, `vegetarian`, `gluten_free`, `lactose_free`, `low_sugar`, `high_protein`, `organic` — dietary boolean filters
* `lang` — en/de/fr/it
* `limit`, `offset` — pagination

### `GET /products/{gtin}`
Full product detail across all public stores.

### `GET /products/{gtin}/nutrition`
Detailed nutrition facts: per_100g, per_serving, Nutri-Score, NOVA group, vitamins, minerals.

## Prices routes — `GET /prices/...`

### `GET /prices/compare/{gtin}`
Cross-store price comparison from `store_price_snapshot`. Returns:
* prices_chf per store
* prices_per_100g per store
* cheapest_store + price
* price_spread_chf + price_spread_pct
* stores_compared

### `GET /prices/history/{gtin}`
Price history grouped by store. Optional `store` filter, `days` param (7–365).

### `GET /prices/latest/{gtin}`
Latest price per store, deduplicated.

## Promotions routes

### `GET /promotions`
Active promotions sorted by discount_pct desc. Optional `store`, `category`, `lang` filters.

## Basket routes — `POST /basket/...`

### `POST /basket/calculate`
Body: `{"items": [{"gtin": "...", "quantity": N}], "lang": "en"}`

Returns:
* `store_totals_chf` — total per store
* `cheapest_complete_store` — cheapest store that has all items
* `store_missing_items` — items not available per store
* `item_breakdown` — per-item price across stores

### `POST /basket/export`
Body: `{"items": [...], "lang": "en|de|fr|it", "list_name": "...", "qr_url": "..."}`

Returns: PDF file download (`application/pdf`)

See Step 19 for full PDF export documentation.

## Scan route

### `POST /scan`
Body: `{"barcode": "...", "store": "...", "user_id": "...", "lang": "en"}`

1. Normalises barcode via `barcode_aliases` table
2. Looks up product in `products`
3. Fetches latest prices per store
4. Logs to `user_scans` if `user_id` provided
5. Returns product details + prices

---

# Step 18 — API tests

## Files

```text
tests/test_api.py
tests/test_decision_engine.py
tests/test_decision_engine_advanced.py
tests/test_ingredient_parser.py
tests/test_ontology_matcher.py
tests/test_ontology_router.py
```

## Total tests passing

```text
108 passed, 0 failed
```

## Test coverage summary

| File | Focus | Tests |
|---|---|---|
| test_api.py | All API endpoints, auth, error codes | 40 |
| test_decision_engine.py | Core verdict logic | 11 |
| test_decision_engine_advanced.py | Real-world edge cases | 45 |
| test_ingredient_parser.py | Normalisation, E-numbers, nesting | 5 |
| test_ontology_matcher.py | Multi-language matching | 5 |
| test_ontology_router.py | Category routing, deduplication | 12 |

## Run command

```bash
export PYTHONPATH=/workspaces/Swiss-Basket-AI
python -m pytest tests/ -v -W ignore::DeprecationWarning
```

## Advanced test scenarios covered

* Alcohol in baked goods (rum cake, tiramisu, wine gums) → not halal
* Pork gelatin in sweets (Haribo-style) → not halal, not vegetarian
* Beef gelatin (no pork) → halal passes
* Honey, beeswax, carmine, casein, whey → not vegan
* GF label + coeliac trigger present → not GF
* `vegan_likely` suppressed when `vegan = True`
* `vegan_likely` shown with `confidence: medium`
* Multilingual package labels (EN/DE/FR/IT)
* Sulphites in wine, histamine in aged cheese
* Complex products: fondue (alcohol + dairy + regional), salmon (histamine + sulphites), baby formula (vitamins + minerals + kids)

---

# Step 19 — Shopping list PDF export

## What was done

A multilingual PDF shopping list export was implemented.

## Files

```text
backend/services/export_service.py
backend/api/routes/basket.py  (POST /basket/export added)
```

## Dependencies added

```text
reportlab==4.2.5
qrcode[pil]==8.0
pillow==11.1.0
```

## Features

* 4 languages: EN / DE / FR / IT
* Items grouped by aisle/category (fresh produce first, frozen last)
* Dietary badges per item (Halal, Vegan, GF, Bio, etc.)
* Store colour coding (Migros orange, Coop red, Aldi blue, Lidl blue)
* Price per item + line totals
* Basket totals per store
* Cheapest store highlighted with ★
* QR code (top right) linking to digital list
* WiseMarket branding + date footer
* A4 format, clean Swiss design

## Category aisle order in PDF

fresh_produce → dairy → dairy_alternative → meat → fish → bakery → pantry → frozen → beverages → snacks → plant_protein → other

## Test command

```bash
curl -s -X POST "http://localhost:8000/basket/export" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"gtin": "7610000100001", "quantity": 2},
      {"gtin": "7610000500001", "quantity": 1},
      {"gtin": "7610001100001", "quantity": 3}
    ],
    "lang": "de",
    "qr_url": "https://wisemarket.ch"
  }' \
  --output shopping_list_de.pdf
```

## Verified output

All 4 language PDFs generated successfully:

| File | Size |
|---|---|
| shopping_list_en.pdf | 4,384 bytes |
| shopping_list_de.pdf | 4,434 bytes |
| shopping_list_fr.pdf | 4,447 bytes |
| shopping_list_it.pdf | 4,443 bytes |

---

# Step 20 — Dockerfile and deployment prep

## Files

```text
Dockerfile
.dockerignore
requirements.txt
```

## Dockerfile

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Run locally

```bash
source .venv/bin/activate
export PYTHONPATH=/workspaces/Swiss-Basket-AI
uvicorn backend.api.main:app --reload --port 8000
```

## API docs (auto-generated)

```
http://localhost:8000/docs      ← Swagger UI
http://localhost:8000/redoc     ← ReDoc
```

---

# Current git history

```
d561490  feat: shopping list PDF export in EN/DE/FR/IT
5513656  feat: API v2 complete - routes, tests, ontology router expanded
7a5520d  feat: API v2 - products, prices, promotions, basket, scan routes + Dockerfile
134a5f7  expand decision engine v2 - 30 verdicts, multilingual packages, expanded router
b514559  expand all 66 ontology CSVs with full Swiss multilingual data
```

---

# Current completed architecture

## Data layer
* 66 ontology CSV files
* Schema 1: 32 tables, 53 indexes, 7 views, 10 triggers, 9 functions
* Schema 2: 30 tables, 36 indexes, 12 views
* Seed data: 51 products, 5 stores, prices, nutrition, user data

## Runtime intelligence layer
* Ingredient parser
* Ontology router (15 categories)
* Ontology matcher
* Decision engine (30+ verdicts, multilingual packages)

## API layer
* 10 endpoints across 5 route modules
* PDF export (4 languages)
* Rate limiting, Sentry, admin auth
* 108 tests passing

## Infrastructure
* Supabase (PostgreSQL) — live
* GitHub Codespace — dev environment
* Dockerfile ready for Railway/Render deploy

---

# Current technical state

```
Ontology + Supabase + Runtime Intelligence + Live API + PDF Export
```

The system can:
* fetch real Swiss supermarket products
* parse ingredients
* route ontology groups by category
* match ontology terms in 4 languages
* evaluate 30+ food verdicts
* compare prices across 5 stores
* calculate basket totals
* export shopping lists as PDF in EN/DE/FR/IT
* return structured API responses

---

# What is next — remaining steps

1. **Agent endpoint** — `POST /agent/query`
   Connect chat/voice/search to an LLM (Groq via LiteLLM). Natural language → DB query → LLM refiner → smart answer.

2. **Scraper pipeline**
   Python scraper agents for Migros, Coop, Aldi writing into `etl.staging_products` → validation → promote to `products`.

3. **Frontend**
   React app connecting to all API endpoints. Screens: scan, search, browse, basket, profile.

4. **User authentication**
   Supabase Auth integration. Link `user_id` to actual user accounts.

5. **Analytics worker**
   Nightly job reading from `events.*` and writing aggregates to `analytics.*`.

6. **Ontology improvement workflow**
   Pipeline: `user_feedback` → `verdict_dispute_analytics` → `ontology_improvement_queue` → human review → ontology update.

7. **B2B reports layer**
   Anonymised dietary trend and price intelligence reports for retailers and food brands.

8. **Railway deployment**
   Push to GitHub → Railway auto-deploy. Add `railway.toml` config.

---

# File locations reference

```
Swiss-Basket-AI/
├── backend/
│   ├── api/
│   │   ├── main.py                    ← FastAPI app
│   │   ├── db.py                      ← Supabase client
│   │   └── routes/
│   │       ├── products.py            ← search + detail + nutrition
│   │       ├── prices.py              ← compare + history + latest
│   │       ├── promotions.py          ← active promotions
│   │       ├── basket.py              ← calculate + export PDF
│   │       └── scan.py                ← barcode scan
│   ├── config/
│   │   └── stores.py                  ← store registry
│   ├── models/
│   │   └── __init__.py
│   ├── services/
│   │   ├── decision_engine.py         ← 30+ verdicts + packages
│   │   ├── ingredient_parser.py       ← raw text → token list
│   │   ├── ontology_matcher.py        ← token → ontology hit
│   │   ├── ontology_router.py         ← category → groups
│   │   └── export_service.py          ← PDF shopping list
│   ├── etl/
│   │   ├── split_by_store.py
│   │   └── supabase_ingest.py
│   └── normalizer/
│       └── ontology_loader.py
├── data/
│   ├── ontology/                      ← 66 CSV files
│   ├── prices_by_store/               ← price CSVs
│   └── products_by_store/             ← product CSVs
├── database/
│   ├── schema_1_v2_1_migration_safe.sql
│   ├── schema_1_v2_1_reset.sql
│   ├── schema_02_analytics_events.sql
│   ├── seed_data.sql
│   └── patch_001_image_fields.sql
├── tests/
│   ├── test_api.py
│   ├── test_decision_engine.py
│   ├── test_decision_engine_advanced.py
│   ├── test_ingredient_parser.py
│   ├── test_ontology_matcher.py
│   └── test_ontology_router.py
├── .env                               ← SUPABASE_URL, SUPABASE_KEY, etc.
├── Dockerfile
├── requirements.txt
└── docs/
    └── technical_steps.md             ← this file
```
# Technical Steps — Continuation from Step 20

---

# Step 21 — LLM Client (Provider-Agnostic)

## What was done

A provider-agnostic LLM wrapper was built using LiteLLM. Swap LLM provider by changing one env var — no code changes needed.

## File

```text
backend/services/llm_client.py
```

## Dependencies added

```text
litellm
```

## Environment variables

```env
GROQ_API_KEY=gsk_...
LLM_INTENT_MODEL=groq/llama-3.1-8b-instant
LLM_REFINER_MODEL=groq/llama-3.3-70b-versatile
LLM_FALLBACK_MODEL=groq/llama-3.1-8b-instant
```

## Why Groq

Groq is the fastest inference available. `llama-3.1-8b-instant` handles intent detection in ~230ms. `llama-3.3-70b-versatile` handles response refinement in ~390ms.

## Key functions

```python
call_intent(messages, max_tokens=200)   # fast model, low temp (0.1)
call_refiner(messages, max_tokens=150)  # larger model, higher temp (0.4)
build_messages(system, user)            # standard format
build_messages_with_history(system, history, user)  # with conversation context (last 6 turns)
```

## Provider swap

To switch from Groq to OpenAI, change `.env`:
```env
LLM_INTENT_MODEL=gpt-4o-mini
LLM_REFINER_MODEL=gpt-4o
OPENAI_API_KEY=sk_...
```
No code changes needed.

## Verified working models (Groq, March 2026)

```
✅ groq/llama-3.1-8b-instant
✅ groq/llama-3.3-70b-versatile
❌ groq/llama3-8b-8192       (decommissioned)
❌ groq/llama3-70b-8192      (decommissioned)
❌ groq/gemma2-9b-it         (decommissioned)
❌ groq/mixtral-8x7b-32768   (decommissioned)
```

---

# Step 22 — Agent Service

## What was done

A full agent pipeline was built connecting user input → intent detection → DB queries → LLM refinement → personalised response.

## File

```text
backend/services/agent.py
```

## Pipeline

```
Input (text/voice/barcode)
  ↓
_extract_search_term()     ← LLM extracts key product noun
  ↓
_detect_intent()           ← LLM classifies into 9 intents
  ↓
_load_user_profile()       ← reads user_preferences from DB
_load_chat_history()       ← reads last 6 turns from DB
  ↓
Route to DB agent          ← deterministic data fetch
  ↓
_compose_and_refine()      ← LLM writes final answer
  ↓
Save to user_chat_history  ← memory for next turn
  ↓
Return response + products
```

## 9 intents

```
find_product      → "show me oat milk"
check_dietary     → "is this halal?"
price_check       → "where is milk cheapest?"
compare_stores    → "migros vs coop for pasta"
basket_advice     → "what's cheapest for my list?"
scan_lookup       → barcode / GTIN lookup
nutrition_query   → "how much protein in chicken?"
promotion_search  → "what is on sale today?"
general           → anything else
```

## Personalisation

```python
generate_greeting(user_id, lang, user_name)
```

- Guest: generic welcome in correct language
- Known user: greets by name, references dietary profile and budget

Example for Ahmed (halal, budget CHF 15, prefers Migros/Coop):
> "Hello Ahmed, I'm happy to assist you with your shopping needs, ensuring that all products meet your halal dietary preferences. How can I help you find the perfect items within your budget of CHF 15.0 at Migros or Coop today?"

## Similar products fallback

When exact search returns 0 results:
1. Search without dietary filter → find non-compliant products
2. Search for dietary-compliant alternatives in same category
3. Return both with honest explanation

---

# Step 23 — Agent API Route

## File

```text
backend/api/routes/agent.py
```

## Endpoints

### `POST /agent/query`

```json
{
  "input": "show me halal chicken",
  "lang": "en",
  "user_id": "optional-uuid",
  "mode": "chat",
  "store": null
}
```

Returns:
```json
{
  "response": "Here are halal chicken options...",
  "intent": "find_product",
  "products": [...]
}
```

### `GET /agent/greeting`

```
GET /agent/greeting?lang=en&user_id=xxx&user_name=Ahmed
```

Returns personalised greeting based on user profile.

## Tested responses

| Input | Intent | Result |
|---|---|---|
| "where is milk cheapest?" | price_check | CHF 1.29 Aldi, 1.45 Migros, 1.50 Coop |
| "show me halal chicken" | find_product | 2 halal chicken products |
| "was ist heute im Angebot?" | promotion_search | 4 promotions in German |
| Guest greeting | — | Generic EN/DE/FR/IT welcome |
| Ahmed greeting | — | Personal halal-aware greeting |

---

# Step 24 — React PWA Frontend

## What was done

A full React Progressive Web App was built with Vite + Tailwind.

## Location

```text
frontend/wisemarket/
```

## Stack

```
Vite 8          ← build tool
React 18        ← UI framework
React Router    ← navigation
Tailwind CSS    ← styling
Lucide React    ← icons
@zxing/library  ← barcode scanning
```

## Design

- Dark mode primary (easier in bright store lighting)
- Swiss red `#E63946` accent
- Fonts: Syne (headers) + DM Sans (body)
- Mobile-first, PWA-ready

## Pages

| Route | Page | Purpose |
|---|---|---|
| `/` | Home | Greeting + quick actions + today's deals |
| `/search` | Search | Product search + AI chat in one tab |
| `/scan` | Scan | Camera barcode scanner + manual GTIN |
| `/basket` | Basket | Shopping list + price comparison + PDF export |
| `/product/:gtin` | Product | Full product detail, prices, nutrition |
| `/settings` | Settings | Language, dietary preferences, dark/light mode |
| `/chat` | Chat | Dedicated AI chat page |

## Key features

- **Combined search** — toggle between product search and AI chat in same input
- **GTIN auto-detect** — typing 8-14 digits redirects to product page
- **Voice input** — Web Speech API, language-aware (de-CH, fr-CH, it-CH)
- **Barcode scanner** — camera via @zxing, animated scan line
- **Basket persistence** — localStorage, survives page refresh
- **Dark/light mode** — toggle in Settings, stored in localStorage
- **Language** — EN/DE/FR/IT, stored in localStorage, affects all API calls
- **Dietary preferences** — toggle switches in Settings, auto-filter search
- **Product badges** — 30+ ontology tags displayed with colour coding
- **Retailer links** — direct link to product on Migros/Coop/Aldi/Lidl
- **Nutrition tabs** — per 100g + per serving + Nutri-Score circle
- **Price bars** — neutral store comparison bars (no "cheapest" label)
- **Add to basket** — button on product page, confirms with green flash
- **PDF export** — from basket page, triggers download

## PWA config

```text
frontend/wisemarket/public/manifest.json
```

```json
{
  "name": "WiseMarket",
  "theme_color": "#E63946",
  "display": "standalone",
  "background_color": "#0D0D0F"
}
```

## Build

```bash
cd frontend/wisemarket
npm run build
# Output: dist/ (694KB JS, 10KB CSS)
```

## Dev

```bash
# Terminal 1 — Backend
uvicorn backend.api.main:app --port 8000

# Terminal 2 — Frontend
cd frontend/wisemarket
npm run dev -- --host 0.0.0.0 --port 5173
```

Vite proxies `/api/*` to `http://localhost:8000`.

---

# Step 25 — Open Food Facts Ingestion

## What was done

Real Swiss product data was ingested from the Open Food Facts public API into Supabase.

## File

```text
backend/etl/ingest_open_food_facts.py
```

## Source

```
https://world.openfoodfacts.org — Swiss country filter
```

## Results

| Metric | Value |
|---|---|
| Products ingested | 9,886 |
| Products skipped (no name/GTIN) | 114 |
| Pages fetched | 100 × 100 = 10,000 |
| Time to ingest | ~18 minutes |

## Tag counts after ingestion

| Tag | Products |
|---|---|
| halal | 9,546 |
| vegan | 7,862 |
| gluten_free | 8,258 |
| lactose_free | 8,116 |
| vegetarian | 9,714 |

## What gets ingested per product

- GTIN (EAN-13)
- Name in EN / DE / FR / IT
- Brand
- Category (mapped from OFF categories)
- Ingredients (raw text)
- Allergens (contains + may_contain)
- Ontology tags (JSONB)
- Nutri-Score (A–E)
- NOVA group (1–4)
- Full nutrition per 100g
- Image URL (stored as reference only — never downloaded)

## Ontology tag logic

```python
# Halal: no pork, no alcohol in name/ingredients/category
has_pork    = any keyword in [porc, schwein, pork, lard, bacon, jambon...]
has_alcohol = any keyword in [alcool, bière, vin, whisky, vodka, rum, gin, wine...]
tags["halal"] = not has_pork and not has_alcohol

# Vegan: no dairy/egg/fish allergens
tags["vegan"] = "milk" not in contains and "eggs" not in contains and "fish" not in contains

# Non-food filter: shampoo, cosmetics, soap → excluded entirely
is_nonfood = any keyword in [shampoo, shampoing, cosmetic, lotion, savon, soap...]
if is_nonfood: return None  # skip product
```

## Category mapping

15 categories mapped from multilingual OFF category strings:
dairy, dairy_alternative, meat, fish, bakery, beverages, pantry, snacks, frozen, fresh_produce, plant_protein, other

## Run command

```bash
cd /workspaces/Swiss-Basket-AI
export PYTHONPATH=/workspaces/Swiss-Basket-AI
python backend/etl/ingest_open_food_facts.py
```

## Store name in DB

All OFF products use `store = "open_food_facts"` in the products table.

## Re-ingestion

Re-running the script upserts on `gtin, store` conflict — safe to re-run.

## Important: JSONB fix

After initial ingestion, ontology_tags were stored as JSON strings. A fix script was run to convert all to proper JSONB:

```bash
python /tmp/fix_jsonb.py
```

This enables Supabase JSONB filtering:
```python
.eq("ontology_tags->>halal", "true")
```

---

# Step 26 — Store config updated

## What was done

`open_food_facts` was added to `PUBLIC_STORES` so the API includes OFF products in all searches.

## File

```text
backend/config/stores.py
```

## Current stores

| Store | Public | Type |
|---|---|---|
| migros | ✅ | playwright scraper (pending) |
| coop | ✅ | playwright scraper (pending) |
| aldi | ✅ | httpx_bs4 scraper (pending) |
| lidl | ✅ | httpx_bs4 scraper (pending) |
| denner | ❌ | pending |
| open_food_facts | ✅ | API ingestion ✅ |

---

# Current DB state (March 2026)

```
products table:
  open_food_facts store  → 9,886 real Swiss products
  migros/coop/aldi/lidl  → 51 seed products (test data)
  TOTAL                  → ~9,937 products

nutrition_facts          → populated for OFF products with nutrition data
product_prices           → seed data only (scraper needed for live prices)
store_price_snapshot     → seed data only
```

---

# Current git log

```
[latest]  feat: 9886 real Swiss products from Open Food Facts
84daac0   feat: agent endpoint with Groq LLM
d561490   feat: shopping list PDF export in EN/DE/FR/IT
5513656   feat: API v2 complete - routes, tests, ontology router expanded
7a5520d   feat: API v2 - products, prices, promotions, basket, scan routes
134a5f7   expand decision engine v2 - 30 verdicts, multilingual packages
b514559   expand all 66 ontology CSVs with full Swiss multilingual data
```

---

# What remains — updated next steps

1. **Price scraper** — Migros/Coop/Aldi/Lidl live prices (biggest gap)
2. **Auth** — Supabase Auth, link user_id to real accounts
3. **Deploy** — Railway or Render, production environment
4. **Analytics worker** — nightly events → aggregates job
5. **More OFF data** — currently 10K of 102K Swiss products ingested
6. **Ontology improvement** — feedback loop from users to ontology CSVs
