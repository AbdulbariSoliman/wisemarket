# ============================================================
# WISEMARKET — MIGROS PRICE SCRAPER (API-based)
# ============================================================
# Uses Migros internal API intercepted via Playwright
# Gets real prices, GTINs, images, names
# Run: python backend/etl/scraper_migros.py
# ============================================================
import asyncio, json, os, sys, time, uuid
from datetime import date
from typing import Optional

from backend.config.settings import ROOT_DIR_STR, ENV_FILE_STR
sys.path.insert(0, ROOT_DIR_STR)
os.chdir(ROOT_DIR_STR)
from dotenv import load_dotenv
load_dotenv(ENV_FILE_STR)

from playwright.async_api import async_playwright
from tqdm import tqdm
from backend.api.db import get_supabase_client

STORE    = "migros"
TODAY    = date.today().isoformat()
SLEEP    = 1.5
BATCH    = 50

SEARCH_TERMS = [
    "milch", "butter", "käse", "joghurt", "rahm", "quark",
    "poulet", "hähnchen", "rindfleisch", "schweinefleisch", "hackfleisch",
    "lachs", "thunfisch", "fischfilet", "garnelen",
    "brot", "toast", "brötchen", "gipfeli", "croissant",
    "pasta", "spaghetti", "penne", "reis", "nudeln",
    "olivenöl", "sonnenblumenöl", "rapsöl",
    "zucker", "mehl", "salz", "pfeffer",
    "schokolade", "kekse", "chips", "nüsse", "müesli",
    "wasser", "orangensaft", "apfelsaft", "kaffee", "tee",
    "äpfel", "bananen", "tomaten", "karotten", "zwiebeln", "kartoffeln",
    "eier", "tofu", "hummus", "linsen", "kichererbsen",
    "shampoo", "zahnpasta",  # will be filtered as non-food
    "waschpulver", "seife",
]

CATEGORY_MAP = {
    "Milchprodukte": "dairy",
    "Milch": "dairy",
    "Butter": "dairy",
    "Käse": "dairy",
    "Joghurt": "dairy",
    "Fleisch": "meat",
    "Poulet": "meat",
    "Fisch": "fish",
    "Meeresfrüchte": "fish",
    "Brot": "bakery",
    "Backwaren": "bakery",
    "Pasta": "pantry",
    "Reis": "pantry",
    "Öl": "pantry",
    "Getränke": "beverages",
    "Wasser": "beverages",
    "Früchte": "fresh_produce",
    "Gemüse": "fresh_produce",
    "Snacks": "snacks",
    "Schokolade": "snacks",
    "Eier": "dairy",
    "Tiefkühl": "frozen",
}

NON_FOOD = ["shampoo", "zahnpasta", "waschpulver", "seife", "reiniger",
            "waschmittel", "körperpflege", "haarpflege", "kosmetik"]


def map_category(breadcrumb: list) -> str:
    for crumb in breadcrumb:
        name = crumb.get("name", "")
        for key, cat in CATEGORY_MAP.items():
            if key.lower() in name.lower():
                return cat
    return "other"


def is_non_food(name: str, breadcrumb: list) -> bool:
    name_lower = name.lower()
    return any(x in name_lower for x in NON_FOOD) or \
           any(any(x in c.get("name","").lower() for x in
               ["körperpflege","haushalt","hygiene","kosmetik","reinigung"])
               for c in breadcrumb)


def build_ontology_tags(name: str, breadcrumb: list) -> dict:
    cat = map_category(breadcrumb)
    name_lower = name.lower()

    has_pork    = any(x in name_lower for x in ["schwein","speck","schinken","salami","wurst","lard","porc"])
    has_alcohol = any(x in name_lower for x in ["bier","wein","wine","bière","alkohol","spirits","vodka","whisky"])
    has_halal_cert = any(x in name_lower for x in ["halal","حلال"])
    is_regional = any(x in name_lower for x in ["aus der region","region","regional","schweizer","suisse"])
    is_bio      = any(x in name_lower for x in ["bio","biologisch","organic","biologique"])

    # Meat/fish: halal ONLY if explicitly certified
    # Non-meat: halal if no pork + no alcohol (dairy, pantry, snacks etc don't need cert)
    if cat in ["meat", "fish"]:
        halal = has_halal_cert and not has_pork and not has_alcohol
    else:
        halal = not has_pork and not has_alcohol

    return {
        "halal":        halal,
        "vegetarian":   cat not in ["meat","fish"] and not has_pork,
        "vegan":        cat not in ["meat","fish","dairy"] and not has_pork,
        "gluten_free":  not any(x in name_lower for x in ["brot","pasta","mehl","weizen","gerste","dinkel"]),
        "lactose_free": cat != "dairy",
        "organic":      is_bio,
        "regional":     is_regional,
        "is_bio":       is_bio,
        "is_regional":  is_regional,
    }


async def scrape_term(page, term: str) -> list:
    """Load search page and capture API responses."""
    results = []

    async def handle_response(response):
        if 'product-display/public/v4/product-cards' in response.url and response.status == 200:
            try:
                data = await response.json()
                if isinstance(data, list):
                    results.extend(data)
            except:
                pass

    page.on('response', handle_response)

    try:
        await page.goto(
            f"https://www.migros.ch/de/search?query={term}",
            timeout=20000, wait_until="networkidle"
        )
        await page.wait_for_timeout(2000)
    except Exception as e:
        pass
    finally:
        page.remove_listener('response', handle_response)

    return results


def process_product(p: dict) -> Optional[tuple]:
    """Extract product + price data from Migros API response."""
    name = p.get("title") or p.get("name") or ""
    breadcrumb = p.get("breadcrumb") or []

    if is_non_food(name, breadcrumb):
        return None

    gtins = p.get("gtins") or []
    gtin  = gtins[0] if gtins else None
    if not gtin:
        gtin = str(p.get("migrosId") or "").zfill(13)

    offer = p.get("offer") or {}
    price_data = offer.get("price") or {}
    price = price_data.get("effectiveValue")
    adv_price = price_data.get("advertisedValue")

    if not price:
        return None

    is_promo = adv_price and adv_price > price
    discount = round((1 - price/adv_price)*100, 1) if is_promo else None

    # Image URL — replace {stack} placeholder
    images = p.get("images") or []
    image_url = None
    if images:
        img = images[0].get("url","")
        image_url = img.replace("{stack}", "ok-100-0")

    category = map_category(breadcrumb)
    ontology  = build_ontology_tags(name, breadcrumb)

    product = {
        "gtin":             gtin,
        "store":            STORE,
        "name_de":          name[:500],
        "name_en":          name[:500],
        "brand":            None,
        "category":         category,
        "ontology_tags":    ontology,
        "allergens":        {"contains":[],"may_contain":[]},
        "image_url":        image_url,
        "image_source":     "retailer_url" if image_url else None,
        "source_url":       p.get("productUrls","")[:500] or None,
        "ontology_version": "v2.0",
        "is_active":        True,
        "is_verified":      False,
    }

    price_row = {
        "gtin":               gtin,
        "store":              STORE,
        "price_chf":          round(price, 2),
        "original_price_chf": round(adv_price, 2) if is_promo else None,
        "is_promotion":       bool(is_promo),
        "discount_pct":       discount,
        "promotion_label":    "Aktion" if is_promo else None,
        "price_date":         TODAY,
    }

    return product, price_row


async def main():
    print("=" * 55)
    print("WISEMARKET — Migros Scraper (API mode)")
    print(f"Date:  {TODAY}")
    print(f"Terms: {len(SEARCH_TERMS)}")
    print("=" * 55)

    supabase = get_supabase_client()

    all_products  = {}  # gtin → product dict
    all_prices    = {}  # gtin → price dict

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox','--disable-dev-shm-usage']
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="de-CH",
        )
        page = await context.new_page()

        # Accept cookies
        try:
            await page.goto("https://www.migros.ch/de", timeout=15000)
            await page.wait_for_timeout(2000)
            for selector in [
                'button:has-text("Alle akzeptieren")',
                'button:has-text("Accept all")',
                '[data-testid="cookie-accept"]',
            ]:
                btn = await page.query_selector(selector)
                if btn:
                    await btn.click()
                    await page.wait_for_timeout(1000)
                    print("Cookies accepted")
                    break
        except:
            pass

        for term in tqdm(SEARCH_TERMS, desc="Scraping Migros"):
            raw = await scrape_term(page, term)
            for item in raw:
                result = process_product(item)
                if result is None:
                    continue
                prod, price = result
                gtin = prod["gtin"]
                if gtin and gtin not in all_products:
                    all_products[gtin] = prod
                    all_prices[gtin]   = price

            await asyncio.sleep(SLEEP)

        await browser.close()

    print(f"\nUnique products scraped: {len(all_products)}")
    products_list = list(all_products.values())
    prices_list   = list(all_prices.values())

    # Upsert products in batches
    inserted_products = 0
    for i in range(0, len(products_list), BATCH):
        chunk = products_list[i:i+BATCH]
        try:
            supabase.table("products").upsert(
                chunk, on_conflict="gtin,store"
            ).execute()
            inserted_products += len(chunk)
        except Exception as e:
            print(f"Product batch error: {e}")

    print(f"Products upserted: {inserted_products}")

    # Get product IDs for price linking
    gtins = [p["gtin"] for p in products_list]
    id_map = {}
    for i in range(0, len(gtins), 100):
        resp = supabase.table("products").select("id,gtin") \
            .in_("gtin", gtins[i:i+100]) \
            .eq("store", STORE).execute()
        for r in resp.data:
            id_map[r["gtin"]] = r["id"]

    # Upsert prices
    price_rows = []
    for price in prices_list:
        pid = id_map.get(price["gtin"])
        if pid:
            price["product_id"] = pid
            price_rows.append(price)

    inserted_prices = 0
    for i in range(0, len(price_rows), BATCH):
        chunk = price_rows[i:i+BATCH]
        try:
            supabase.table("product_prices").upsert(
                chunk, on_conflict="product_id,store,price_date"
            ).execute()
            inserted_prices += len(chunk)
        except Exception as e:
            print(f"Price batch error: {e}")

    print(f"Prices upserted: {inserted_prices}")

    # Rebuild price snapshots
    print("Rebuilding price snapshots...")
    try:
        # Rebuild snapshots for migros GTINs
        gtins_to_rebuild = list(all_products.keys())[:100]
        for g in gtins_to_rebuild:
            try:
                supabase.rpc("fn_rebuild_price_snapshot", {"p_gtin": g}).execute()
            except:
                pass
        print("Snapshots rebuilt")
    except Exception as e:
        print(f"Snapshot rebuild: {e}")

    print(f"\n✅ Done!")
    count_p = supabase.table("products").select("id",count="exact").eq("store",STORE).execute()
    count_pr = supabase.table("product_prices").select("id",count="exact").eq("store",STORE).execute()
    print(f"   Migros products: {count_p.count}")
    print(f"   Migros prices:   {count_pr.count}")

if __name__ == "__main__":
    asyncio.run(main())
