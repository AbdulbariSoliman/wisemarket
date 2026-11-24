import json, os, re, time, uuid
from typing import Optional
import requests
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()
import sys
from backend.config.settings import ROOT_DIR_STR
sys.path.insert(0, ROOT_DIR_STR)
from backend.services.product_tags import tags_from_ingredients  # noqa: E402
from backend.api.db import get_supabase_client

PAGES_TO_FETCH   = 100
PAGE_SIZE        = 100
STORE_NAME       = "open_food_facts"
BATCH_SIZE       = 50
SLEEP_BETWEEN    = 1.0
ONTOLOGY_VERSION = "v2.0"

HEADERS = {"User-Agent": "WiseMarket/1.0 (contact: your-email@example.com)"}

BASE_URL = (
    "https://world.openfoodfacts.org/cgi/search.pl"
    "?action=process"
    "&tagtype_0=countries&tag_contains_0=contains&tag_0=switzerland"
    "&fields=code,product_name,product_name_de,product_name_fr,product_name_it,"
    "brands,categories,ingredients_text,allergens,traces,"
    "energy-kcal_100g,energy-kj_100g,fat_100g,saturated-fat_100g,"
    "carbohydrates_100g,sugars_100g,fiber_100g,proteins_100g,salt_100g,"
    "nutriscore_grade,nova_group,image_url"
    "&json=1"
    f"&page_size={PAGE_SIZE}"
)

# Open Food Facts puts most plant-based foods under a generic parent category
# such as "Aliments et boissons à base de végétaux" ("plant-based foods AND
# beverages"). The word "boissons"/"beverages" in that parent made cereals,
# biscuits and spreads map to "beverages", so these parents are removed first.
GENERIC_OFF_PARENTS = [
    "aliments et boissons à base de végétaux", "aliments d'origine végétale",
    "plant-based foods and beverages", "plant-based foods",
    "pflanzliche lebensmittel und getränke", "pflanzliche lebensmittel",
    "alimenti e bevande a base vegetale", "alimenti di origine vegetale",
    "snacks sucrés", "sweet snacks",
]


def map_category(raw):
    if not raw: return "other"
    r = raw.lower()
    for parent in GENERIC_OFF_PARENTS:
        r = r.replace(parent, " ")
    # Breakfast cereals / muesli / granola belong to pantry, never beverages
    if any(x in r for x in ["céréales pour petit-déjeuner", "breakfast cereals",
                              "frühstückscerealien", "muesli", "müesli", "müsli",
                              "granola", "cereali per la colazione"]):
        return "pantry"
    # Non-food first — return other immediately
    if any(x in r for x in ["cosmétique","cosmetic","hygiene","hygiène","beauté","beauty",
                              "shampoo","savon","seife","soap","nettoyant"]):
        return "other"
    # Dairy
    if any(x in r for x in ["lait","milch","milk","fromage","käse","cheese",
                              "yaourt","joghurt","yogurt","beurre","butter",
                              "crème fraîche","quark","cottage","mozzarella",
                              "gruyère","emmental","parmesan","ricotta"]):
        return "dairy"
    # Plant milks
    if any(x in r for x in ["oat","hafer","avoine","soja","soy","amande","mandel",
                              "coco","kokos","riz","reis","hemp","chanvre"]) and        any(x in r for x in ["drink","boisson","lait","milk","milch"]):
        return "dairy_alternative"
    # Meat
    if any(x in r for x in ["viande","fleisch","meat","bœuf","rind","beef",
                              "porc","schwein","pork","poulet","huhn","chicken",
                              "dinde","truthahn","turkey","agneau","lamm","lamb",
                              "jambon","ham","saucisse","wurst","sausage","steak"]):
        return "meat"
    # Fish
    if any(x in r for x in ["poisson","fisch","fish","saumon","lachs","salmon",
                              "thon","thunfisch","tuna","crevette","shrimp","prawn",
                              "cabillaud","kabeljau","cod","sardine","hareng","hering"]):
        return "fish"
    # Bakery
    if any(x in r for x in ["pain","brot","bread","boulangerie","bäckerei",
                              "gâteau","kuchen","cake","biscuit","keks","cookie",
                              "pâtisserie","croissant","brioche","muffin","tarte"]):
        return "bakery"
    # Fresh produce — before beverages to catch fruit juices correctly
    if any(x in r for x in ["fruits frais","frisches obst","fresh fruit",
                              "légumes frais","frisches gemüse","fresh vegetable",
                              "salade","salat","salad","herbes","kräuter","herbs",
                              "châtaigne","kastanie","chestnut","champignon","pilz"]):
        return "fresh_produce"
    # Beverages
    if any(x in r for x in ["eau","wasser","water","jus","saft","juice",
                              "boisson","getränk","beverage","bière","bier","beer",
                              "vin","wein","wine","café","kaffee","coffee",
                              "thé","tee","tea","soda","limonade","lemonade",
                              "sirop","sirup","syrup","smoothie","energy drink"]):
        return "beverages"
    # Pantry
    if any(x in r for x in ["pâtes","pasta","nudeln","riz","reis","rice",
                              "céréales","getreide","grain","légumineuses",
                              "hülsenfrüchte","legumes","haricot","bohne","bean",
                              "lentille","linse","lentil","pois chiche","kichererbse",
                              "huile","öl","oil","vinaigre","essig","vinegar",
                              "conserve","konserve","sauce","soupe","suppe","soup",
                              "miel","honig","honey","confiture","marmelade","jam",
                              "farine","mehl","flour","sucre","zucker","sugar"]):
        return "pantry"
    # Snacks
    if any(x in r for x in ["chocolat","schokolade","chocolate","snack",
                              "chips","bonbon","süssigkeit","candy","confiserie",
                              "noix","nuss","nut","amande","mandel","almond",
                              "pistache","pistazie","noisette","haselnuss",
                              "barre","riegel","bar","granola","müsli","muesli"]):
        return "snacks"
    # Frozen
    if any(x in r for x in ["surgelé","tiefkühl","frozen","surgel"]):
        return "frozen"
    # Plant protein
    if any(x in r for x in ["tofu","seitan","tempeh","protéine végétale",
                              "pflanzenprotein","plant protein"]):
        return "plant_protein"
    # Fresh produce (broader)
    if any(x in r for x in ["fruits","obst","fruit","légumes","gemüse",
                              "vegetable","plante"]):
        return "fresh_produce"
    return "other"

def map_allergens(raw, traces):
    known = ["gluten","milk","eggs","nuts","peanuts","soy","fish","shellfish","sesame","sulphites"]
    raw_lower    = (raw or "").lower()
    traces_lower = (traces or "").lower()
    contains    = [a for a in known if a in raw_lower]
    may_contain = [a for a in known if a in traces_lower and a not in contains]
    return {"contains": contains, "may_contain": may_contain}

def map_ontology_tags(allergens, categories, nutriscore, name="", ingredients=""):
    tags = {}
    contains = allergens.get("contains", [])
    cat = (categories or "").lower()
    has_pork    = any(x in cat for x in ["porc","schwein","pork","lard"])
    has_alcohol = any(x in cat for x in ["alcool","alkohol","bière","bier","vin","wein"])
    tags["halal"]        = not has_pork and not has_alcohol
    tags["vegan"]        = "milk" not in contains and "eggs" not in contains and "fish" not in contains
    tags["vegetarian"]   = "fish" not in contains and "shellfish" not in contains and not has_pork
    tags["gluten_free"]  = "gluten" not in contains
    tags["lactose_free"] = "milk" not in contains
    tags["nut_free"]     = "nuts" not in contains and "peanuts" not in contains
    if nutriscore in ("a","b"): tags["low_sugar"] = True
    # When the ingredient list is known, use the same analysis pipeline as
    # /analyze/{gtin}, so search filters and product pages agree. The
    # allergen-based values above remain the fallback for products without
    # ingredients.
    from_ingredients = tags_from_ingredients(ingredients, map_category(categories), name)
    if from_ingredients:
        tags.update(from_ingredients)
        tags["lactose_free"] = tags["lactose_free"] and "milk" not in contains
        tags["gluten_free"]  = tags["gluten_free"] and "gluten" not in contains
    return tags

def clean_gtin(code):
    if not code: return None
    code = re.sub(r'\D', '', str(code))
    if len(code) < 8 or len(code) > 14: return None
    return code.zfill(13) if len(code) == 12 else code

def _float(v):
    try:
        f = float(v)
        return f if 0 <= f < 100000 else None
    except: return None

def fetch_page(page):
    try:
        resp = requests.get(f"{BASE_URL}&page={page}", timeout=30, headers=HEADERS)
        resp.raise_for_status()
        return resp.json().get("products", [])
    except Exception as e:
        print(f"  Page {page} failed: {e}")
        return []

def process_product(p):
    gtin = clean_gtin(p.get("code"))
    if not gtin: return None
    name_en = p.get("product_name") or p.get("product_name_de") or p.get("product_name_fr") or p.get("product_name_it") or ""
    if not name_en.strip(): return None
    categories    = p.get("categories") or ""
    allergens     = map_allergens(p.get("allergens"), p.get("traces"))
    nutriscore    = (p.get("nutriscore_grade") or "").lower()
    ontology_tags = map_ontology_tags(
        allergens, categories, nutriscore,
        name=name_en,
        ingredients=p.get("ingredients_text") or ""
    )
    # Skip non-food products entirely
    if ontology_tags.get("is_non_food"):
        return None
    image_url     = p.get("image_url") or None
    prod = {
        "id":               str(uuid.uuid4()),
        "gtin":             gtin,
        "store":            STORE_NAME,
        "name_en":          (name_en or "")[:500] or None,
        "name_de":          (p.get("product_name_de") or "")[:500] or None,
        "name_fr":          (p.get("product_name_fr") or "")[:500] or None,
        "name_it":          (p.get("product_name_it") or "")[:500] or None,
        "brand":            (p.get("brands") or "")[:200] or None,
        "category":         map_category(categories),
        "ingredients_raw":  (p.get("ingredients_text") or "")[:2000] or None,
        "ontology_tags":    ontology_tags,
        "allergens":        allergens,
        "image_url":        image_url,
        "image_source":     "open_food_facts" if image_url else None,
        "ontology_version": ONTOLOGY_VERSION,
        "is_active":        True,
        "is_verified":      False,
    }
    nutr = {
        "gtin":              gtin,
        "nutriscore":        nutriscore.upper() if nutriscore else None,
        "nova_group":        int(p["nova_group"]) if str(p.get("nova_group","")).strip().isdigit() else None,
        "energy_kcal_100":   _float(p.get("energy-kcal_100g")),
        "energy_kj_100":     _float(p.get("energy-kj_100g")),
        "fat_100":           _float(p.get("fat_100g")),
        "saturated_fat_100": _float(p.get("saturated-fat_100g")),
        "carbs_100":         _float(p.get("carbohydrates_100g")),
        "sugars_100":        _float(p.get("sugars_100g")),
        "fibre_100":         _float(p.get("fiber_100g")),
        "protein_100":       _float(p.get("proteins_100g")),
        "salt_100":          _float(p.get("salt_100g")),
    }
    return prod, nutr

def ingest_batch(supabase, products, nutrition_list):
    try:
        supabase.table("products").upsert(products, on_conflict="gtin,store").execute()
    except Exception as e:
        print(f"  Product upsert error: {e}")
        return 0
    try:
        gtins  = [p["gtin"] for p in products]
        id_map = {r["gtin"]: r["id"] for r in
                  supabase.table("products").select("id,gtin").in_("gtin", gtins).eq("store", STORE_NAME).execute().data}
        nutr_rows = []
        for n in nutrition_list:
            pid = id_map.get(n["gtin"])
            if not pid: continue
            if not any(n.get(k) is not None for k in ["energy_kcal_100","protein_100","fat_100"]): continue
            nutr_rows.append({
                "product_id":        pid,
                "nutri_score":       n["nutriscore"] if n["nutriscore"] in ("A","B","C","D","E") else None,
                "nova_group":        n["nova_group"],
                "energy_kcal_100":   n["energy_kcal_100"],
                "energy_kj_100":     n["energy_kj_100"],
                "fat_100":           n["fat_100"],
                "saturated_fat_100": n["saturated_fat_100"],
                "carbs_100":         n["carbs_100"],
                "sugars_100":        n["sugars_100"],
                "fibre_100":         n["fibre_100"],
                "protein_100":       n["protein_100"],
                "salt_100":          n["salt_100"],
                "source":            "open_food_facts",
            })
        if nutr_rows:
            supabase.table("nutrition_facts").upsert(nutr_rows, on_conflict="product_id").execute()
    except Exception as e:
        print(f"  Nutrition error: {e}")
    return len(products)

def main():
    print("=" * 50)
    print("Open Food Facts → Supabase Ingestion")
    print(f"Pages: {PAGES_TO_FETCH} × {PAGE_SIZE} = ~{PAGES_TO_FETCH*PAGE_SIZE} products")
    print("=" * 50)
    supabase = get_supabase_client()
    total_ingested = 0
    total_skipped  = 0

    for page in tqdm(range(1, PAGES_TO_FETCH + 1), desc="Pages"):
        raw = fetch_page(page)
        batch_p, batch_n = [], []
        for p in raw:
            result = process_product(p)
            if result is None:
                total_skipped += 1
                continue
            prod, nutr = result
            batch_p.append(prod)
            batch_n.append(nutr)

        for i in range(0, len(batch_p), BATCH_SIZE):
            total_ingested += ingest_batch(supabase, batch_p[i:i+BATCH_SIZE], batch_n[i:i+BATCH_SIZE])

        time.sleep(SLEEP_BETWEEN)

    print(f"\n✅ Ingested: {total_ingested} | Skipped: {total_skipped}")
    count = supabase.table("products").select("id", count="exact").eq("store", STORE_NAME).execute()
    print(f"DB total (open_food_facts): {count.count}")

if __name__ == "__main__":
    main()