import os
import csv

from backend.config.settings import DATA_DIR_STR

BASE_DIR = DATA_DIR_STR
PRODUCTS_FILE = os.path.join(BASE_DIR, "products.csv")
PRICES_FILE = os.path.join(BASE_DIR, "prices.csv")

PRODUCTS_BY_STORE_DIR = os.path.join(BASE_DIR, "products_by_store")
PRICES_BY_STORE_DIR = os.path.join(BASE_DIR, "prices_by_store")
os.makedirs(PRODUCTS_BY_STORE_DIR, exist_ok=True)
os.makedirs(PRICES_BY_STORE_DIR, exist_ok=True)

stores = ["Migros", "Coop", "Aldi"]

# --- Split Products ---
with open(PRODUCTS_FILE, newline="", encoding="utf-8") as f:
    reader = list(csv.DictReader(f))
    headers = reader[0].keys()

    for store in stores:
        path = os.path.join(PRODUCTS_BY_STORE_DIR, f"{store.lower()}_products.csv")
        with open(path, "w", newline="", encoding="utf-8") as f_out:
            writer = csv.DictWriter(f_out, fieldnames=headers)
            writer.writeheader()
            for row in reader:
                if row.get("store", "").lower() == store.lower():
                    writer.writerow(row)
        print(f"Created {path}")

# --- Split Prices ---
with open(PRICES_FILE, newline="", encoding="utf-8") as f:
    reader = list(csv.DictReader(f))
    headers = reader[0].keys()

    for store in stores:
        path = os.path.join(PRICES_BY_STORE_DIR, f"{store.lower()}_prices.csv")
        with open(path, "w", newline="", encoding="utf-8") as f_out:
            writer = csv.DictWriter(f_out, fieldnames=headers)
            writer.writeheader()
            for row in reader:
                if row.get("store", "").lower() == store.lower():
                    writer.writerow(row)
        print(f"Created {path}")

print("\n✅ Store-specific product and price CSVs generated")