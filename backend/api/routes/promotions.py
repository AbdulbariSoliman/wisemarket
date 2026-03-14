# ============================================================
# WISEMARKET — PROMOTIONS ROUTES
# GET /promotions
# GET /promotions/{store}
# ============================================================
from typing import Literal, Optional

from fastapi import APIRouter, Query

from backend.api.db import get_supabase_client
from backend.config.stores import PUBLIC_STORES

router = APIRouter()


@router.get("")
def get_promotions(
    store: Optional[str] = Query(None, description="Filter by store"),
    category: Optional[str] = Query(None, description="Filter by category"),
    lang: Literal["en", "de", "fr", "it"] = "en",
    limit: int = Query(20, ge=1, le=100),
):
    """
    Active promotions across all public stores.
    Sorted by discount size (biggest first).
    """
    supabase = get_supabase_client()

    stores_to_query = [store.lower()] if store else PUBLIC_STORES

    query = (
        supabase.table("product_prices")
        .select(
            "gtin, store, price_chf, original_price_chf, discount_pct, "
            "promotion_label, promotion_ends, price_per_100g, price_date, "
            "products(name_en, name_de, name_fr, name_it, brand, category, image_url)"
        )
        .eq("is_promotion", True)
        .in_("store", stores_to_query)
        .order("discount_pct", desc=True)
        .limit(limit)
    )

    if category:
        query = query.eq("products.category", category.lower())

    resp = query.execute()

    def get_name(product_join: dict) -> Optional[str]:
        if not product_join:
            return None
        return (
            product_join.get(f"name_{lang}")
            or product_join.get("name_en")
        )

    results = []
    for row in resp.data:
        product = row.get("products") or {}
        results.append({
            "gtin":               row.get("gtin"),
            "store":              row.get("store"),
            "name":               get_name(product),
            "brand":              product.get("brand"),
            "category":           product.get("category"),
            "image_url":          product.get("image_url"),
            "promo_price_chf":    row.get("price_chf"),
            "original_price_chf": row.get("original_price_chf"),
            "discount_pct":       row.get("discount_pct"),
            "promotion_label":    row.get("promotion_label"),
            "promotion_ends":     str(row.get("promotion_ends")) if row.get("promotion_ends") else None,
            "price_per_100g":     row.get("price_per_100g"),
        })

    return {"count": len(results), "promotions": results}
