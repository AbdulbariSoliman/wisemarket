import os
import csv
import json
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# -------------------------
# Helpers
# -------------------------
def safe_json(val):
    if val is None:
        return {}
    val = val.strip()
    if val == "":
        return {}
    try:
        return json.loads(val)
    except:
        return {}

# -------------------------
# Supabase
# -------------------------
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are missing from .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# -------------------------
# Paths
# -------------------------
from backend.config.settings import DATA_DIR_STR

BASE_DIR = DATA_DIR_STR
PRODUCTS_DIR = os.path.join(BASE_DIR, "products_by_store")
PRICES_DIR = os.path.join(BASE_DIR, "prices_by_store")
ONTOLOGY_DIR = os.path.join(BASE_DIR, "ontology")

STORES = ["Migros", "Coop", "Aldi"]
ONTOLOGY_VERSION = "v1.0"

# -------------------------
# Load ontology
# -------------------------
ontology_data = {}
for file in os.listdir(ONTOLOGY_DIR):
    if file.endswith(".csv"):
        with open(os.path.join(ONTOLOGY_DIR, file), encoding="utf-8") as f:
            ontology_data[file.replace(".csv","")] = list(csv.DictReader(f))

print(f"✅ Loaded {len(ontology_data)} ontology categories")

# -------------------------
# Process stores
# -------------------------
for store in STORES:
    print(f"\n🏬 Processing Store: {store}")

    products_file = os.path.join(PRODUCTS_DIR, f"{store.lower()}_products.csv")
    if not os.path.exists(products_file):
        print("⚠️ No product file, skipping")
        continue

    products = []
    with open(products_file, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            products.append({
                "gtin": row.get("gtin"),
                "store": store,
                "name_en": row.get("name_en"),
                "name_de": row.get("name_de"),
                "name_fr": row.get("name_fr"),
                "name_it": row.get("name_it"),
                "brand": row.get("brand"),
                "category": row.get("category"),
                "ingredients_raw": row.get("ingredients_raw"),
                "ingredients_normalized": {
                    "en": row.get("ingredients_en","").split(";"),
                    "de": row.get("ingredients_de","").split(";"),
                    "fr": row.get("ingredients_fr","").split(";"),
                    "it": row.get("ingredients_it","").split(";")
                },
                "ontology_tags": list(ontology_data.keys()),
                "allergens": row.get("allergens","").split(";"),
                "nutrition": {
                    "per_100g": safe_json(row.get("nutrition_100g")),
                    "per_serving": safe_json(row.get("nutrition_serving"))
                },
                "ontology_version": ONTOLOGY_VERSION,
                "is_active": True
            })

    # -------------------------
    # Batch upsert
    # -------------------------
    gtin_map = {}
    BATCH = 50

    for i in range(0, len(products), BATCH):
        batch = products[i:i+BATCH]
        resp = supabase.table("products_new") \
            .upsert(batch, on_conflict="gtin,store") \
            .execute()

        for item in resp.data:
            gtin_map[item["gtin"]] = item["id"]

        print(f"✅ Uploaded batch {i//BATCH+1}")

    # -------------------------
    # Prices
    # -------------------------
    prices_file = os.path.join(PRICES_DIR, f"{store.lower()}_prices.csv")
    if not os.path.exists(prices_file):
        print("⚠️ No price file, skipping")
        continue

    with open(prices_file, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = gtin_map.get(row.get("gtin"))
            if not pid:
                continue

            price_raw = row.get("price", "").strip()

            if not price_raw or price_raw.lower() == "price":
                print("⚠️ Skipping invalid price row:", row)
                continue

            price_val = float(price_raw)

            supabase.table("product_prices").insert({
                "product_id": pid,
                "price": price_val,
                "currency": "CHF",
                "price_date": row.get("price_date"),
                "unit_price": float(row.get("unit_price", price_val)),
                "promotion_info": safe_json(row.get("promotion_info"))
            }).execute()

            print(f"💰 Price added: {row.get('gtin')}")

print("\n🎉 ETL COMPLETE")
```
