# ============================================================
# WISEMARKET — PRODUCTS ROUTES
# GET /products/search
# GET /products/{gtin}
# GET /products/{gtin}/nutrition
# ============================================================
from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query

from backend.api.db import get_supabase_client
from backend.config.stores import PUBLIC_STORES

router = APIRouter()


def _get_name(product: dict, lang: str) -> Optional[str]:
    return (
        product.get(f"name_{lang}")
        or product.get("name_en")
        or product.get("name_de")
        or product.get("name_fr")
        or product.get("name_it")
    )


@router.get("/search")
def search_products(
    q: Optional[str] = Query(None, description="Search term"),
    store: Optional[str] = Query(None, description="Filter by store"),
    category: Optional[str] = Query(None, description="Filter by category"),
    halal: Optional[bool] = Query(None),
    vegan: Optional[bool] = Query(None),
    vegetarian: Optional[bool] = Query(None),
    gluten_free: Optional[bool] = Query(None),
    lactose_free: Optional[bool] = Query(None),
    low_sugar: Optional[bool] = Query(None),
    high_protein: Optional[bool] = Query(None),
    organic: Optional[bool] = Query(None),
    lang: Literal["en", "de", "fr", "it"] = "en",
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    supabase = get_supabase_client()

    query = supabase.table("products").select(
        "id, gtin, store, name_en, name_de, name_fr, name_it, "
        "brand, category, sub_category, ontology_tags, allergens, "
        "nutrition_cache, pack_size_raw, unit_quantity, unit_type, "
        "image_url, is_active"
    ).eq("is_active", True).in_("store", PUBLIC_STORES)

    if store:
        query = query.eq("store", store.lower())
    if category:
        query = query.eq("category", category.lower())
    if q:
        name_col = f"name_{lang}" if lang in ("en", "de", "fr", "it") else "name_en"
        query = query.ilike(name_col, f"%{q}%")

    dietary_filters = {
        "halal":        halal,
        "vegan":        vegan,
        "vegetarian":   vegetarian,
        "gluten_free":  gluten_free,
        "lactose_free": lactose_free,
        "low_sugar":    low_sugar,
        "high_protein": high_protein,
        "organic":      organic,
    }
    for key, value in dietary_filters.items():
        if value is True:
            query = query.eq(f"ontology_tags->>{key}", "true")

    resp = query.range(offset, offset + limit - 1).execute()

    products = []
    for p in resp.data:
        products.append({
            "gtin":          p.get("gtin"),
            "store":         p.get("store"),
            "name":          _get_name(p, lang),
            "name_en":       p.get("name_en") or "",
            "name_de":       p.get("name_de") or "",
            "name_fr":       p.get("name_fr") or "",
            "name_it":       p.get("name_it") or "",
            "source_url":    p.get("source_url") or "",
            "brand":         p.get("brand"),
            "category":      p.get("category"),
            "sub_category":  p.get("sub_category"),
            "ontology_tags": p.get("ontology_tags"),
            "allergens":     p.get("allergens"),
            "nutrition":     p.get("nutrition_cache"),
            "pack_size_raw": p.get("pack_size_raw"),
            "unit_quantity": p.get("unit_quantity"),
            "unit_type":     p.get("unit_type"),
            "image_url":     p.get("image_url"),
        })

    return {"count": len(products), "offset": offset, "limit": limit, "results": products}


@router.get("/{gtin}/nutrition")
def get_nutrition(gtin: str, store: Optional[str] = Query(None)):
    supabase = get_supabase_client()

    query = supabase.table("products").select("id, store, name_en").eq("gtin", gtin).in_("store", PUBLIC_STORES)
    if store:
        query = query.eq("store", store.lower())
    prod_resp = query.limit(1).execute()

    if not prod_resp.data:
        raise HTTPException(status_code=404, detail=f"Product {gtin} not found")

    product_id = prod_resp.data[0]["id"]
    nutr_resp = supabase.table("nutrition_facts").select("*").eq("product_id", product_id).execute()

    if not nutr_resp.data:
        raise HTTPException(status_code=404, detail="Nutrition data not available")

    n = nutr_resp.data[0]
    return {
        "gtin":         gtin,
        "store":        prod_resp.data[0].get("store"),
        "product_name": prod_resp.data[0].get("name_en"),
        "per_100g": {
            "energy_kcal":   n.get("energy_kcal_100"),
            "energy_kj":     n.get("energy_kj_100"),
            "fat":           n.get("fat_100"),
            "saturated_fat": n.get("saturated_fat_100"),
            "carbs":         n.get("carbs_100"),
            "sugars":        n.get("sugars_100"),
            "fibre":         n.get("fibre_100"),
            "protein":       n.get("protein_100"),
            "salt":          n.get("salt_100"),
        },
        "per_serving": {
            "serving_size_g": n.get("serving_size_g"),
            "energy_kcal":    n.get("energy_kcal_srv"),
            "fat":            n.get("fat_srv"),
            "carbs":          n.get("carbs_srv"),
            "sugars":         n.get("sugars_srv"),
            "protein":        n.get("protein_srv"),
            "salt":           n.get("salt_srv"),
        },
        "nutri_score": n.get("nutri_score"),
        "nova_group":  n.get("nova_group"),
        "vitamins":    n.get("vitamins"),
        "minerals":    n.get("minerals"),
    }


@router.get("/{gtin}")
def get_product(
    gtin: str,
    store: Optional[str] = Query(None),
    lang: Literal["en", "de", "fr", "it"] = "en",
):
    supabase = get_supabase_client()

    query = supabase.table("products").select("*").eq("gtin", gtin).in_("store", PUBLIC_STORES)
    if store:
        query = query.eq("store", store.lower())

    resp = query.execute()

    if not resp.data:
        raise HTTPException(status_code=404, detail=f"Product {gtin} not found")

    results = []
    for p in resp.data:
        results.append({
            "gtin":            p.get("gtin"),
            "store":           p.get("store"),
            "name":            _get_name(p, lang),
            "brand":           p.get("brand"),
            "category":        p.get("category"),
            "sub_category":    p.get("sub_category"),
            "ingredients_raw": p.get("ingredients_raw"),
            "ontology_tags":   p.get("ontology_tags"),
            "allergens":       p.get("allergens"),
            "nutrition":       p.get("nutrition_cache"),
            "pack_size_raw":   p.get("pack_size_raw"),
            "unit_quantity":   p.get("unit_quantity"),
            "unit_type":       p.get("unit_type"),
            "units_per_pack":  p.get("units_per_pack"),
            "image_url":       p.get("image_url"),
            "image_source":    p.get("image_source"),
            "is_verified":     p.get("is_verified"),
            "name_en":         p.get("name_en") or "",
            "name_de":         p.get("name_de") or "",
            "name_fr":         p.get("name_fr") or "",
            "name_it":         p.get("name_it") or "",
            "source_url":      p.get("source_url") or "",
        })

    # Check for a GTIN-exact unified merge (Migros + third-party data)
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

    return {"gtin": gtin, "stores": results, "unified": unified}
