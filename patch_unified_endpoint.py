PATH = "backend/api/routes/products.py"


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

before = '''    return {"gtin": gtin, "stores": results}'''

after = '''    # Check for a GTIN-exact unified merge (Migros + third-party data)
    unified = None
    try:
        uni_resp = (
            supabase.table("unified_products")
            .select("unified_id, canonical_name_en, canonical_name_de, "
                    "canonical_brand, canonical_category, canonical_image_url, "
                    "canonical_ingredients_raw, canonical_nutrition, allergens, "
                    "field_sources")
            .eq("canonical_gtin", gtin)
            .limit(1)
            .execute()
        )
        if uni_resp.data:
            u = uni_resp.data[0]
            unified = {
                "unified_id":       u.get("unified_id"),
                "name_en":          u.get("canonical_name_en"),
                "name_de":          u.get("canonical_name_de"),
                "brand":            u.get("canonical_brand"),
                "category":         u.get("canonical_category"),
                "image_url":        u.get("canonical_image_url"),
                "ingredients_raw":  u.get("canonical_ingredients_raw"),
                "nutrition":        u.get("canonical_nutrition"),
                "allergens":        u.get("allergens"),
                "field_sources":    u.get("field_sources") or {},
            }
    except Exception:
        unified = None

    return {"gtin": gtin, "stores": results, "unified": unified}'''

content, ok = replace_exact(content, before, after, "add unified merge lookup to get_product")

if ok:
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("\nChange applied. File saved.")
else:
    print("\nChange NOT applied (see SKIP/WARN above). File NOT saved.")