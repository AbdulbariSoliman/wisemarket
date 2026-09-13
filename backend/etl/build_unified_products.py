# ============================================================
# WISEMARKET — GTIN-EXACT UNIFIED PRODUCT BUILDER
# ============================================================
import sys

from backend.config.settings import ROOT_DIR_STR
sys.path.insert(0, ROOT_DIR_STR)

from backend.api.db import get_supabase_client

RETAILER_STORE = "migros"
THIRDPARTY_STORE = "open_food_facts"
BATCH = 50


def _valid_gtin(g):
    return bool(g) and g.isdigit() and len(g) in (8, 13, 14)


def _fetch_all(supabase, store):
    rows, start, page = {}, 0, 1000
    while True:
        resp = (
            supabase.table("products")
            .select("id, gtin, store, name_en, name_de, name_fr, name_it, "
                    "brand, category, image_url, source_url, "
                    "ingredients_raw, ingredients_normalized, allergens, nutrition_cache")
            .eq("store", store)
            .range(start, start + page - 1)
            .execute()
        )
        for r in resp.data:
            if _valid_gtin(r.get("gtin")):
                rows[r["gtin"]] = r
        if len(resp.data) < page:
            break
        start += page
    return rows


def _nutrition_for(supabase, product_id):
    resp = (
        supabase.table("nutrition_facts")
        .select("energy_kcal_100, energy_kj_100, fat_100, saturated_fat_100, "
                "carbs_100, sugars_100, fibre_100, protein_100, salt_100, "
                "serving_size_g, nutri_score, nova_group, vitamins, minerals")
        .eq("product_id", product_id)
        .limit(1)
        .execute()
    )
    return resp.data[0] if resp.data else None


def build():
    supabase = get_supabase_client()

    print("Fetching migros products...")
    migros = _fetch_all(supabase, RETAILER_STORE)
    print(f"  migros valid-GTIN rows: {len(migros)}")

    print("Fetching open_food_facts products...")
    off = _fetch_all(supabase, THIRDPARTY_STORE)
    print(f"  OFF valid-GTIN rows: {len(off)}")

    overlap = sorted(set(migros) & set(off))
    print(f"GTIN-exact overlap: {len(overlap)}")

    unified_rows = []
    member_pairs = []

    for gtin in overlap:
        m = migros[gtin]
        o = off[gtin]

        off_nutrition = _nutrition_for(supabase, o["id"]) or o.get("nutrition_cache")

        unified_rows.append({
            "canonical_gtin": gtin,
            "canonical_name_en": m.get("name_en") or o.get("name_en"),
            "canonical_name_de": m.get("name_de") or o.get("name_de"),
            "canonical_name_fr": m.get("name_fr") or o.get("name_fr"),
            "canonical_name_it": m.get("name_it") or o.get("name_it"),
            "canonical_brand": m.get("brand") or o.get("brand"),
            "canonical_category": m.get("category") or o.get("category"),
            "canonical_image_url": m.get("image_url") or o.get("image_url"),
            "canonical_ingredients_raw": o.get("ingredients_raw"),
            "canonical_nutrition": off_nutrition,
            "allergens": o.get("allergens"),
            "field_sources": {
                "name": {"store": RETAILER_STORE, "kind": "retailer"},
                "category": {"store": RETAILER_STORE, "kind": "retailer"},
                "image": {"store": RETAILER_STORE, "kind": "retailer"},
                "price_ref": {"store": RETAILER_STORE, "kind": "retailer"},
                "source_url": {"store": RETAILER_STORE, "kind": "retailer"},
                "brand": {"store": RETAILER_STORE if m.get("brand") else THIRDPARTY_STORE,
                          "kind": "retailer" if m.get("brand") else "third_party"},
                "allergens": {"store": THIRDPARTY_STORE, "kind": "third_party"},
                "ingredients": {"store": THIRDPARTY_STORE, "kind": "third_party"},
                "nutrition": {"store": THIRDPARTY_STORE, "kind": "third_party"},
                "ontology_tags": {"kind": "computed"},
            },
        })
        member_pairs.append((gtin, m["id"], RETAILER_STORE, True, "gtin_exact"))
        member_pairs.append((gtin, o["id"], THIRDPARTY_STORE, False, "gtin_exact"))

    print(f"Upserting {len(unified_rows)} unified_products...")
    for i in range(0, len(unified_rows), BATCH):
        chunk = unified_rows[i:i + BATCH]
        supabase.table("unified_products").upsert(
            chunk, on_conflict="canonical_gtin"
        ).execute()

    gtins = [r["canonical_gtin"] for r in unified_rows]
    id_map = {}
    for i in range(0, len(gtins), 100):
        resp = (
            supabase.table("unified_products")
            .select("unified_id, canonical_gtin")
            .in_("canonical_gtin", gtins[i:i + 100])
            .execute()
        )
        for r in resp.data:
            id_map[r["canonical_gtin"]] = r["unified_id"]

    member_rows = []
    for gtin, product_id, store, is_master, method in member_pairs:
        uid = id_map.get(gtin)
        if not uid:
            continue
        member_rows.append({
            "unified_id": uid,
            "product_id": product_id,
            "store": store,
            "is_master": is_master,
            "match_method": method,
            "similarity_score": 1.0,
        })

    print(f"Upserting {len(member_rows)} unified_product_members...")
    for i in range(0, len(member_rows), BATCH):
        chunk = member_rows[i:i + BATCH]
        supabase.table("unified_product_members").upsert(
            chunk, on_conflict="unified_id,product_id"
        ).execute()

    print("Done.")
    print(f"  unified_products upserted: {len(unified_rows)}")
    print(f"  members upserted:          {len(member_rows)}")


if __name__ == "__main__":
    build()