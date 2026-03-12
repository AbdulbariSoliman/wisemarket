

# Swiss-Basket-AI — Technical Steps Documentation

## Purpose

This document records the technical build steps completed so far in Swiss-Basket-AI, including:

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
* future user memory
* future feedback / ratings
* future authentication

## Why

The project needed a persistent database that can support:

* structured product records
* pricing history
* JSON fields for nutrition and normalized ingredients
* future API access
* future user and scan history

## Why Supabase

Supabase provides:

* managed PostgreSQL
* simple setup
* SQL support
* future auth support
* future storage support
* future vector search support

---

# Step 6 — Supabase tables (concept and current structure)

## Main product intelligence tables

### `products_new`

Stores the main product record.

Typical fields include:

* `id`
* `gtin`
* `store`
* `name_en`
* `name_de`
* `name_fr`
* `name_it`
* `brand`
* `category`
* `ingredients_raw`
* `ingredients_normalized`
* `ontology_tags`
* `allergens`
* `nutrition`
* `is_active`
* `ontology_version`
* `created_at`
* `updated_at`

### Why this table exists

This is the main table used by the runtime API to fetch product data for live analysis.

It stores:

* raw product label data
* parsed/normalized ingredient data
* nutrition data
* multilingual names
* store identity

---

### `product_prices`

Stores price history for products.

Typical fields include:

* `id`
* `product_id`
* `price`
* `currency`
* `promotion_info`
* `price_date`
* `price_last_checked`
* `unit_price`

### Why this table exists

Prices change more often than ingredients or product identity.

Separating prices from products allows:

* historical tracking
* future deal logic
* future cheapest-store comparison
* reduced duplication

---

### `nutrition_facts` (optional)

Stores structured nutrition if kept separately.

Typical fields include:

* `id`
* `product_id`
* `per_100g`
* `per_serving`
* `last_updated`

### Why this table exists

Nutrition can remain inside `products_new.nutrition`, but a separate table is useful if nutrition handling becomes more detailed later.

---

### `ontology_versions` (optional)

Tracks ontology versioning.

Typical fields include:

* `version`
* `applied_at`
* `notes`

### Why this table exists

If ontology rules change later, products can be traced back to the ontology version used during analysis.

---

## Legacy / earlier concept tables

Earlier planning also included concepts such as:

* `products`
* `price_history`
* `policy_tags`
* `unified_products`
* `scrape_failures`

These helped shape the final design, but the current runtime pipeline is centered on:

* `products_new`
* `product_prices`

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

## Why

The ETL populates Supabase with structured data that the API can analyze.

## Important implementation points

* safe JSON handling
* batch upserts
* three-store processing:

  * Migros
  * Coop
  * Aldi
* product and price ingestion

## Result

The ETL completed successfully and product analysis data became queryable from Supabase.

---

# Step 8 — Runtime folder structure cleanup

## What was done

The backend structure was cleaned up and extended to support runtime logic.

New runtime folders were created:

```text
backend/api/
backend/services/
```

Package initializers were added:

```text
backend/api/__init__.py
backend/services/__init__.py
```

## Why

The earlier repository structure had ingestion and ontology loading, but did not yet have a clean place for runtime business logic and API code.

The separation now is:

* `etl/` → ingestion
* `normalizer/` → ontology loading
* `services/` → runtime intelligence logic
* `api/` → FastAPI endpoints

---

# Step 9 — Ingredient parser design

## What was done

A deterministic ingredient parser was designed and implemented.

## File

```text
backend/services/ingredient_parser.py
```

## Why

Raw ingredient labels from Swiss retailers are messy and often include:

* nested parentheses
* percentages
* additives / E-numbers
* punctuation
* formatting noise

The parser converts raw ingredient label text into normalized ingredient tokens.

## Implemented features

* lowercase normalization
* split outside parentheses
* flatten nested ingredients
* remove percentages and simple units
* normalize E-number variants
* preserve order
* deduplicate without losing sequence

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

# Step 10 — Ingredient parser testing

## What was done

The parser was locked with automated tests.

## File

```text
tests/test_ingredient_parser.py
```

## Test coverage

* simple ingredient list
* nested parentheses
* semicolon splitting
* E-number normalization
* empty input

## Command

```bash
python -m pytest tests/test_ingredient_parser.py -q
```

## Result

```text
5 passed
```

---

# Step 11 — Ontology router design

## What was done

An ontology router was created to decide which ontology groups should be checked for a product.

## File

```text
backend/services/ontology_router.py
```

## Why

Checking all ontology groups for every product is unnecessary and harder to maintain.

The router improves the system by:

* always running universal checks
* adding category-specific ontology groups

## Universal groups used

Examples:

* allergens
* animal_products
* promotion_terms
* price_unit_aliases
* sugar_synonyms
* salt_synonyms

## Category examples

* Dairy → lactose / vegan / vegetarian related groups
* Seafood → fish / shellfish / histamine
* Meat → meat / pork
* Snacks → nuts / superfood markers

---

# Step 12 — Ontology router testing

## What was done

Tests were added for the router.

## File

```text
tests/test_ontology_router.py
```

## Test coverage

* empty category
* dairy category
* seafood category
* unknown category

## Command

```bash
python -m pytest tests/test_ontology_router.py -q
```

## Result

```text
4 passed
```

---

# Step 13 — Ontology matcher design

## What was done

An ontology matcher was implemented.

## File

```text
backend/services/ontology_matcher.py
```

## Why

After ingredients are parsed and ontology groups are routed, the system must compare ingredient tokens with ontology terms.

The matcher builds an in-memory search index from ontology data and returns matched terms per ontology group.

## Output example

```python
{
    "allergens": ["milk"],
    "animal_products": ["milk powder"]
}
```

---

# Step 14 — Ontology matcher testing

## What was done

Matcher tests were added.

## File

```text
tests/test_ontology_matcher.py
```

## Test coverage

* single group match
* multi-group match
* no match case
* unknown group
* fish example

## Command

```bash
python -m pytest tests/test_ontology_matcher.py -q
```

## Result

```text
5 passed
```

---

# Step 15 — Decision engine design

## What was done

A decision engine was implemented.

## File

```text
backend/services/decision_engine.py
```

## Why

Parser, router, and matcher only produce evidence. The decision engine turns that evidence into final product verdicts.

## Version 1 verdicts

* halal
* vegan
* vegetarian
* allergen_warning
* regional

## Example rule logic

* pork or alcohol found → halal = false
* animal products found → vegan = false
* pork found → vegetarian = false
* allergen found → allergen_warning = true
* regional labels found → regional = true

---

# Step 16 — Decision engine testing

## What was done

Decision engine tests were added.

## File

```text
tests/test_decision_engine.py
```

## Test coverage

* positive case except vegan
* pork breaks halal + vegetarian
* alcohol breaks halal
* clean product case

## Command

```bash
python -m pytest tests/test_decision_engine.py -q
```

## Result

```text
4 passed
```

---

# Step 17 — Runtime pipeline completed

## What was done

The first full runtime intelligence pipeline was completed:

```text
raw ingredients
→ parser
→ router
→ matcher
→ decision engine
```

## Why this matters

At this point, the project moved from “data storage” to “real product intelligence”.

---

# Step 18 — API database connector

## What was done

A FastAPI database connector was created for Supabase.

## File

```text
backend/api/db.py
```

## Why

The API must connect to Supabase to fetch live product data.

## Important design

Environment variables are used:

* `SUPABASE_URL`
* `SUPABASE_KEY`

---

# Step 19 — FastAPI application wiring

## What was done

The FastAPI app was created and wired to the runtime pipeline.

## File

```text
backend/api/main.py
```

## Why

This exposes the analysis system over HTTP so it can be used by frontend, scanner, chat, or mobile app.

## Main pieces added

* startup lifespan loading
* parser/router/matcher/decision engine loaded once
* root route
* health route
* analyze endpoint

---

# Step 20 — Root endpoint

## Route

```text
GET /
```

## Purpose

Confirms the API is running.

## Example response

```json
{"message":"Swiss Basket AI API is running"}
```

---

# Step 21 — Health endpoint

## Route

```text
GET /health
```

## Purpose

Confirms:

* API is alive
* services loaded correctly
* ontology and runtime components exist in app state

## Example response

```json
{
  "status": "ok",
  "version": "1.0.0",
  "services": {
    "ontology_data": true,
    "parser": true,
    "router": true,
    "matcher": true,
    "decision_engine": true
  }
}
```

---

# Step 22 — Analyze endpoint

## Route

```text
GET /analyze/{gtin}
```

## What it does

1. validates GTIN
2. fetches product from Supabase
3. reads ingredients
4. parses ingredients
5. routes ontology groups
6. matches ontology terms
7. evaluates verdicts
8. returns structured JSON

## Example successful output

```json
{
  "gtin": "1234567890123",
  "store": "Migros",
  "name_en": "Milk 1L",
  "category": "Dairy",
  "ingredients_raw": "milk",
  "ingredients_parsed": ["milk"],
  "ontology_groups": [
    "allergens",
    "animal_products",
    "promotion_terms",
    "price_unit_aliases",
    "sugar_synonyms",
    "salt_synonyms",
    "lactose_free_labels",
    "vegan_markers",
    "vegetarian_markers"
  ],
  "matches": {
    "allergens": ["milk"],
    "animal_products": ["milk"],
    "promotion_terms": [],
    "price_unit_aliases": [],
    "sugar_synonyms": [],
    "salt_synonyms": [],
    "lactose_free_labels": [],
    "vegan_markers": [],
    "vegetarian_markers": []
  },
  "verdicts": {
    "halal": true,
    "vegan": false,
    "vegetarian": true,
    "allergen_warning": true,
    "regional": false,
    "reasons": {
      "pork_hits": [],
      "alcohol_hits": [],
      "animal_hits": ["milk"],
      "allergen_hits": ["milk"],
      "regional_hits": []
    }
  }
}
```

---

# Step 23 — API successfully running

## What was done

The FastAPI server was started successfully with:

```bash
python -m uvicorn backend.api.main:app --reload
```

## What was verified

* startup loaded ontology and services
* `/` route worked
* `/health` worked
* `/analyze/{gtin}` worked
* end-to-end product analysis returned valid JSON

---

# Step 24 — Current runtime test summary

## Passing test files

* `tests/test_ingredient_parser.py`
* `tests/test_ontology_router.py`
* `tests/test_ontology_matcher.py`
* `tests/test_decision_engine.py`

## Total passing tests

```text
18 passed
```

---

# Current completed architecture

## Data layer

* ontology CSV system
* ontology generator
* ontology validation
* ontology loader
* Supabase schema
* ETL ingestion

## Runtime intelligence layer

* ingredient parser
* ontology router
* ontology matcher
* decision engine

## API layer

* Supabase connector
* FastAPI app
* root endpoint
* health endpoint
* analyze endpoint

---

# Current technical state

The project is now at:

```text
Ontology + Supabase + Runtime Intelligence + Live API
```

This means the system can already:

* fetch real products
* parse ingredients
* route ontology groups
* match ontology terms
* evaluate food verdicts
* return structured API responses

---

# What is left — next high-level steps

1. Add product endpoint with latest price
2. Add price data into `/analyze/{gtin}` output
3. Add API tests
4. Add natural-language `/ask` endpoint
5. Add user memory / feedback tables
6. Add authentication and security layer
7. Expand verdict coverage:

   * keto
   * gluten-free
   * lactose-free
   * low sugar
   * histamine
8. Improve deployment and production config
9. Improve ontology update workflow
10. Add recommendation / ML layer later

---

# Suggested file for this document

```text
docs/technical_steps.md
```
