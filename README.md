# 🇨🇭 Swiss Basket AI — Technical README

**Swiss Basket AI** is a high-integrity Retail Intelligence Platform for Switzerland.
It synchronizes data across **Migros, Coop, and Aldi** to provide deterministic, neutral, and auditable product comparisons.

---

## 🧠 Core Philosophy — The Rule of Four

1. **SQL is the Truth**
   Prices and stock are stored and retrieved from a relational database. The AI never invents values.

2. **Logic is the Guard**
   Safety rules (pork, alcohol, animal-derived) are enforced by a deterministic rule engine.

3. **LLM is the Voice**
   AI is limited to intent parsing and natural language explanation.

4. **Hash is the Law**
   Ingredient and price updates are triggered only when cryptographic hashes change.

---

## 🏗️ System Architecture

### **Tier 1 — Smart Harvester (Extraction)**

* Playwright-based scrapers for Migros, Coop, and Aldi.
* Uses ETags and price hashing to detect changes.
* Normalizes all prices to **CHF per 100g / 100ml**.

---

### **Tier 2 — Truth Layer (Processing)**

* **Matcher:**
  Uses embeddings for product identity matching only (never for safety decisions).

* **Certifier (Rule Engine):**
  Applies `policy_tags` using a Swiss Ingredient Ontology:

  * Pork blocklist
  * Alcohol blocklist

* **Conflict Detector:**
  Flags mismatches between marketing labels and ingredient origin.

---

### **Tier 3 — Agentic Brain (LangGraph)**

* **Intent Agent:** Converts user language into structured queries.
* **Policy Agent:** Filters products using `policy_tags`.
* **Validator:** Final gate. Blocks stale data (>24h) and hallucinated output.

---

### **Tier 4 — Delivery (Next.js UI)**

* Displays only factual flags:
  *“Contains pork”*, *“Contains alcohol”*.
* No religious or lifestyle labels.
* Every result links to the original retailer URL.

---

## 🗂️ Data Schema (Supabase)

Star Schema:

* **products**

  * `product_id`
  * `ingredients_sha256`
  * `normalized_name`

* **price_history**

  * `product_id`
  * `price_chf`
  * `price_per_100`
  * `timestamp`

* **policy_tags**

  * `product_id`
  * `contains_pork`
  * `contains_alcohol`
  * `contains_animal_derived`

---

## 🔄 Implementation Roadmap

| Phase   | Focus             | Deliverable                  |
| ------- | ----------------- | ---------------------------- |
| Phase 1 | Data Foundation   | Supabase schema + harvesters |
| Phase 2 | Safety & Identity | Rule engine + matcher        |
| Phase 3 | Orchestration     | LangGraph with validator     |
| Phase 4 | Delivery          | Comparison UI                |

---

## 🛡️ Safety & Neutrality Standards

* No religious labeling.
* No AI-based safety classification.
* Prices older than 24 hours are hidden.
* All data is source-verifiable.

---

