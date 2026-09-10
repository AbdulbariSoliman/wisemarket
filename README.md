# WiseMarket 🇨🇭

A smart shopping assistant that knows what's in your food, where it's cheapest, and what you can eat — in any Swiss language.

WiseMarket is a Swiss grocery intelligence platform: search or scan a product, compare its price across stores, get a deterministic breakdown of dietary/nutrition/allergen flags, and query a conversational AI assistant about your shopping.

---

## System design

WiseMarket is a **retrieval-grounded, tool-using agent system** layered on top of a deterministic rules engine — not a pure LLM application. This distinction matters: the parts of the system that must never be wrong (prices, allergens, exact product matches) are handled by non-probabilistic code, and the LLM is scoped narrowly to natural-language understanding and generation.

### Retrieval-augmented generation (structured, not vector)

Instead of a vector store, the retrieval layer is a structured relational database (Postgres via Supabase). A user query is parsed for intent, the relevant rows are fetched via typed SQL/PostgREST queries, and only that retrieved context is passed to the LLM for generation. This is **grounded generation**: the model is never permitted to answer from parametric memory alone, which eliminates price/availability hallucination by construction rather than by prompting.

### Agentic orchestration

The agent layer (`backend/services/agent.py`) implements a single-pass **intent → tool-routing → generation** loop:

1. **Intent classification** — an LLM call (via LiteLLM, routed to Groq-hosted models) maps the user's natural-language input to a discrete intent (search, price comparison, basket operation, general Q&A).
2. **Tool routing** — deterministic dispatch to the matching backend function. No tool call is itself an LLM decision beyond intent classification; the actual database operations are fixed, typed, and testable in isolation.
3. **State/memory injection** — `user_preferences` and `user_chat_history` are read and merged into context, giving the agent session-level personalization without any client-side state management.
4. **Grounded generation** — the LLM produces the final natural-language response, constrained to the retrieved tool outputs and injected memory.

This is currently a **linear single-agent pipeline**, not a multi-agent graph (no LangGraph, no supervisor/worker topology, no inter-agent message passing). It is intentionally the simplest architecture that satisfies the grounding requirement.

### Deterministic decision engine (non-LLM)

The dietary/nutrition/safety layer (`backend/services/decision_engine.py` + `ontology_matcher.py` + `ontology_router.py`) is pure rule-based logic — ingredient strings are parsed, matched against a curated ontology (allergens, dietary markers, additive categories), and evaluated into ~30 boolean/enum verdicts (halal, vegan, gluten-free, allergen warnings, and more). **No LLM call is in this path.** This is a deliberate architectural boundary: safety-relevant classification must be deterministic, auditable, and regression-testable — properties an LLM classifier doesn't reliably provide.

```
                              ┌─────────────┐
                              │ User query  │
                              └──────┬──────┘
                                     ▼
                       ┌───────────────────────────┐
                       │ Intent detection (LLM)     │
                       │ Groq via LiteLLM           │
                       └─────────────┬─────────────┘
                                     ▼
                       ┌───────────────────────────┐
                       │ Tool router (deterministic)│
                       └──────┬──────────────┬─────┘
                              ▼              ▼
                  ┌───────────────────┐ ┌──────────────────┐
                  │ Database tools     │ │ User memory       │
                  │ search / prices /  │ │ preferences +     │
                  │ basket calc        │ │ chat history      │
                  └─────────┬──────────┘ └────────┬──────────┘
                             └──────────┬──────────┘
                                        ▼
                       ┌───────────────────────────┐
                       │ Response generation (LLM)  │
                       │ grounded in retrieved data  │
                       └─────────────┬─────────────┘
                                     ▼
                              ┌─────────────┐
                              │ Answer      │
                              └─────────────┘
```

*(Rendered interactively earlier in this conversation as a diagram — same structure, ASCII fallback here for the repo.)*

### Tool-calling standardization (not yet adopted)

The agent's tool layer today is bespoke Python function dispatch, not a standardized protocol. **Model Context Protocol (MCP)** is a candidate standard for exposing the database tools (search, price compare, basket calc) as a uniform, introspectable tool surface that any MCP-compatible client or agent runtime could call — this would decouple the tool implementations from the specific agent loop currently hardcoded in `agent.py`, and is a natural extension point if the agent layer grows in complexity (see roadmap). It is **not currently implemented**; the only MCP surface present anywhere in this stack is an incidental one exposed by the local Supabase CLI's development tooling, unrelated to the application's own agent architecture.

### Full request architecture

```
React (Vite) PWA
   │  fetch → VITE_API_URL
   ▼
FastAPI backend
   ├─ /analyze/{gtin}   → ontology matcher → decision engine → verdicts
   ├─ /products/*       → search, detail, nutrition
   ├─ /prices/*         → compare, history, latest
   ├─ /basket/*         → calculate, nutrition, PDF export
   ├─ /scan             → barcode → product + prices
   └─ /agent/*          → intent detection → tool routing → grounded generation
   │
   ▼
Supabase Postgres
   public schema: products, product_prices, nutrition_facts,
                  store_price_snapshot, price_history, user_*
   analytics / events / etl schemas: reserved, not yet wired
   │
   ▲ writes
ETL pipeline
   scraper_migros.py (Playwright)     — live
   ingest_open_food_facts.py (REST)   — live
   Coop / Aldi / Lidl / Denner        — planned
```

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

Schema is version-controlled at `backend/schema/schema.sql`, covering all four schemas the app touches (`public`, `analytics`, `events`, `etl`). Reproduce locally:

```bash
psql "<your-postgres-connection-string>" -f backend/schema/schema.sql
```

**Current status:** Row Level Security is enabled on every `public` table, but no policies are defined. The application currently authenticates to Postgres via the Supabase `service_role` key, which bypasses RLS — a deliberate interim state until per-user JWT authentication is implemented (see [Known limitations](#known-limitations)).

---

## Testing

- **Pure-logic tests** (`pytest -m "not integration"`) — ingredient parser, ontology matcher, decision engine. No database required.
- **Integration tests** (`pytest -m integration`) — real API endpoints against a live database. Require `SUPABASE_URL`/`SUPABASE_KEY` pointing at a seeded instance.

Full suite locally, against a disposable local database:

```bash
supabase start                                    # local Postgres + PostgREST via Docker
DB_URL="postgresql://postgres:postgres@127.0.0.1:54322/postgres"
psql "$DB_URL" -f backend/schema/schema.sql
psql "$DB_URL" -f backend/schema/seed_test.sql

export SUPABASE_URL="http://127.0.0.1:54321"
export SUPABASE_KEY="<local SERVICE_ROLE_KEY from: supabase status -o env>"
export ADMIN_API_KEY="test-admin-key"
pytest -q
```

CI (`.github/workflows/ci.yml`) runs both tiers on every push/PR, spinning up a fresh local Supabase instance for the integration job — nothing touches production data.

---

## Known limitations

- **No RLS policies.** The app relies on `service_role` bypassing RLS entirely. Client-supplied `user_id` is trusted without verification — no real per-user data isolation exists yet.
- **Ingestion coverage is partial.** Only Migros and Open Food Facts are live; Coop, Aldi, Lidl, Denner scrapers don't exist.
- **The decision engine's output isn't surfaced client-side.** `/analyze` and the verdict pipeline work correctly and are test-covered, but the Product screen doesn't call the endpoint yet.
- **No agent-side output validation.** The generation step has no staleness check (e.g. rejecting prices >24h old) or evidence-grounding assertion beyond what's implicit in the retrieval step.
- **`analytics`/`events`/`etl` schemas are provisioned but unused** — no code reads or writes them yet.

---

## Roadmap

**Near-term**
1. Wire `/analyze` into the Product screen — surface the decision engine's verdicts, currently the system's core differentiator, in the actual UI.
2. Supabase Auth + real RLS policies: derive `user_id` server-side from a verified JWT; write `SELECT` policies for catalog tables (public reads) and per-user (`auth.uid() = user_id`) policies for personal data tables. Auth and RLS must ship together — switching off `service_role` before policies exist breaks every read.

**Mid-term**
3. Expand ingestion: Coop, Aldi, Lidl, Denner scrapers, templated off the working Migros scraper — one store at a time, fully verified before starting the next.
4. Add an output-validation layer to the agent: reject stale prices, refuse generation without retrieved evidence, and log grounding failures for review.
5. Evaluate exposing the database tool layer via **MCP**, decoupling tool implementations from the current hardcoded agent loop — worth revisiting once (or if) the agent's tool surface grows beyond the current three operations.

**Longer-term**
6. Decide on the `analytics`/`events`/`etl` schemas: either implement the aggregation worker that populates them, or formally deprecate/remove them from the schema.
7. Ongoing: remove unused architecture scaffolding, keep this document synchronized with the actual codebase as it evolves.

---

## License

MIT License

Copyright (c) 2026 Abdulbari Soliman

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
