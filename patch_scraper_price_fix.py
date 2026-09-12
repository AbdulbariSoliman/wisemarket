PATH = "backend/etl/scraper_migros.py"


def replace_exact(content, before, after, label):
    if before not in content:
        print(f"  SKIP/WARN [{label}]: expected text not found.")
        return content, False
    if content.count(before) > 1:
        print(f"  WARN [{label}]: text appears more than once - manual check needed.")
        return content, False
    print(f"  OK [{label}]")
    return content.replace(before, after, 1), True


with open(PATH, "r", encoding="utf-8") as f:
    content = f.read()

before_1 = '''    offer = p.get("offer") or {}
    price_data = offer.get("price") or {}
    price = price_data.get("effectiveValue")
    adv_price = price_data.get("advertisedValue")

    if not price:
        return None'''

after_1 = '''    offer = p.get("offer") or {}
    price_data = offer.get("price") or {}
    price = price_data.get("effectiveValue")
    adv_price = price_data.get("advertisedValue")

    if not price:
        return None

    quantity_raw = offer.get("quantity")
    unit_price_data = price_data.get("unitPrice") or {}
    price_per_100g = unit_price_data.get("value")
    unit_price_unit = unit_price_data.get("unit")'''

content, ok1 = replace_exact(content, before_1, after_1, "capture quantity + unitPrice")

before_2 = '''    price_row = {
        "gtin":               gtin,
        "store":              STORE,
        "price_chf":          round(price, 2),
        "original_price_chf": round(adv_price, 2) if is_promo else None,
        "is_promotion":       bool(is_promo),
        "discount_pct":       discount,
        "promotion_label":    "Aktion" if is_promo else None,
        "price_date":         TODAY,
    }'''

after_2 = '''    price_row = {
        "gtin":               gtin,
        "store":              STORE,
        "price_chf":          round(price, 2),
        "original_price_chf": round(adv_price, 2) if is_promo else None,
        "is_promotion":       bool(is_promo),
        "discount_pct":       discount,
        "promotion_label":    "Aktion" if is_promo else None,
        "price_date":         TODAY,
        "pack_size_raw":      quantity_raw,
        "price_per_100g":     round(price_per_100g, 4) if price_per_100g is not None else None,
    }'''

content, ok2 = replace_exact(content, before_2, after_2, "add pack_size_raw + price_per_100g to price_row")

if ok1 and ok2:
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("\nBoth changes applied. File saved.")
else:
    print("\nOne or more changes were NOT applied. File NOT saved.")