Perfect — now we document **everything end-to-end**, including:

✅ Ontology
✅ Generator
✅ Normalizer
✅ Folder structure
✅ Supabase
✅ How data flows
✅ What you already ran
✅ Why each step exists

Below is a **complete README section** from **Step 1 → Supabase** that you can paste directly into `README.md`.

---

# 🇨🇭 Swiss-Basket-AI — Full System Documentation (Steps 1 → Supabase)

## 🎯 Project Purpose

Swiss-Basket-AI builds a **multilingual food intelligence engine** for Swiss retailers (Migros, Coop, Aldi Suisse).

It analyzes:
• ingredients
• allergens
• dietary labels
• marketing claims
• sustainability
• nutrition
• promotions

Using:
➡ Ontology (CSV)
➡ Normalization
➡ Matching
➡ Database (Supabase)

Languages:
🇬🇧 EN
🇩🇪 DE
🇫🇷 FR
🇮🇹 IT

---

## 🧱 Repository Structure

```text
Swiss-Basket-AI/
├── backend/
│   ├── normalizer/
│   │   ├── __init__.py
│   │   └── ontology_loader.py
│   ├── matcher/
│   ├── validator/
│   ├── certifier/
│   └── database/
├── data/
│   └── ontology/
│       ├── *.csv                # 66 ontology categories
│       └── tools/
│           └── generate_ontology.py
├── frontend/
├── tests/
├── venv/
└── README.md
```

---

## 🧩 STEP 1 — Ontology Design

Each ontology file = one **semantic category**

Examples:
• allergens
• pork
• vegan
• sugar
• additives
• promotions
• nutrition
• sustainability

Each file structure:

```csv
term,en,de,fr,it
pork,pork,Schwein,porc,maiale
bacon,bacon,Speck,bacon,bacon
```

Design rules:
✔ one concept per row
✔ multilingual
✔ lowercase normalized
✔ Swiss retailer vocabulary
✔ Migros / Coop / Aldi wording

---

## ⚙️ STEP 2 — Ontology Generator

File:

```text
data/ontology/tools/generate_ontology.py
```

Purpose:
• auto-create all ontology CSVs
• ensure structure
• avoid manual errors
• reproducible

Run:

```bash
cd data/ontology/tools
python generate_ontology.py
```

Output:

```text
Created: animal_products.csv
Created: vegan_markers.csv
...
Generated 66 ontology CSV files
```

---

## 🔍 STEP 3 — Ontology Validation

Check content:

```bash
wc -l data/ontology/*.csv
```

Example output:

```text
214 total
66 files
```

Ensures:
✔ no empty CSV
✔ content exists
✔ all categories present

---

## 🧠 STEP 4 — Ontology Loader (Normalizer)

File:

```text
backend/normalizer/ontology_loader.py
```

Responsibilities:
• load all CSVs
• normalize case
• split synonyms
• store in memory

In-memory structure:

```python
{
  "pork": ["pork", "schwein", "porc", "maiale"],
  "vegan_markers": ["vegan", "pflanzlich", "végétal", "vegano"],
  ...
}
```

Run:

```bash
python backend/normalizer/ontology_loader.py
```

Output:

```text
Loaded 66 ontology categories
child_friendly_markers: 2 terms
bundle_terms: 1 terms
...
```

---

## 💾 STEP 5 — Memory Model

• CSV = persistent storage
• Python dict = runtime memory
• Size ≈ < 1 MB
• Reloaded at startup

Data flow:

```text
CSV files
   ↓
ontology_loader.py
   ↓
RAM dictionary
   ↓
Matcher / Validator / Certifier
```

---

## 🗄️ STEP 6 — Supabase Integration

Supabase is used as:
✔ Product database
✔ Scan result storage
✔ User data
✔ Audit history

### Supabase Tables (concept)

#### products

| column      | type |
| ----------- | ---- |
| ean         | text |
| name        | text |
| brand       | text |
| ingredients | text |
| language    | text |

#### scans

| column    | type        |
| --------- | ----------- |
| scan_id   | uuid        |
| ean       | text        |
| flags     | jsonb       |
| timestamp | timestamptz |

#### ontology_results

| column   | type  |
| -------- | ----- |
| ean      | text  |
| category | text  |
| matches  | jsonb |

---

## 🔁 STEP 7 — Full Processing Flow

```text
Product OCR text
      ↓
Normalizer
      ↓
Ontology Matcher
      ↓
Conflict Checker
      ↓
Certifier Engine
      ↓
Supabase storage
      ↓
Frontend UI
```

---

## 🧪 Intelligence Layers (future-ready)

• Ambiguity Resolver
• Hidden Source Detector
• Logic Conflict Checker
• Precision Scaling

Example rule:

IF label says "dairy free"
AND ingredient contains "casein"
→ flag "Misleading Label"

---

## 📐 Design Principles

✔ multilingual
✔ Swiss market focused
✔ transparent logic
✔ reproducible
✔ extensible
✔ regulation-aware
✔ AI-ready

---

## 🧾 What Has Been Built So Far

✅ 66 ontology CSV files
✅ multilingual terms
✅ generator script
✅ ontology loader
✅ memory normalization
✅ folder structure
✅ Supabase design
✅ validation steps

---

## 🛠️ How to Add New Ontology Category

1. Add file name to generator
2. Add rows
3. Run generator
4. Run loader
5. Verify count

---




