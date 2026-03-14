# ============================================================
# WISEMARKET — BASKET ROUTES
# POST /basket/calculate
# ============================================================
from typing import Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.api.db import get_supabase_client
from backend.config.stores import PUBLIC_STORES

router = APIRouter()


class BasketItem(BaseModel):
    gtin: str
    quantity: int = 1


class BasketRequest(BaseModel):
    items: List[BasketItem]
    preferred_store: Optional[str] = None
    dietary_filter: Optional[str] = None
    lang: Literal["en", "de", "fr", "it"] = "en"


@router.post("/calculate")
def calculate_basket(req: BasketRequest):
    """
    Calculate basket total per store for a list of GTINs.
    Returns:
      - total per store
      - cheapest store for full basket
      - per-item breakdown
      - any items not available in a store
    """
    if not req.items:
        raise HTTPException(status_code=422, detail="Basket is empty")

    supabase = get_supabase_client()
    gtins = [item.gtin for item in req.items]
    qty_map = {item.gtin: item.quantity for item in req.items}

    # Fetch latest prices for all GTINs
    resp = (
        supabase.table("product_prices")
        .select(
            "gtin, store, price_chf, price_per_100g, is_promotion, "
            "discount_pct, promotion_label, price_date, "
            "products(name_en, name_de, name_fr, name_it, ontology_tags)"
        )
        .in_("gtin", gtins)
        .in_("store", PUBLIC_STORES)
        .order("price_date", desc=True)
        .execute()
    )

    # Build price map: {gtin: {store: price_row}}
    price_map: Dict[str, Dict[str, dict]] = {}
    seen = set()
    for row in resp.data:
        key = (row["gtin"], row["store"])
        if key not in seen:
            seen.add(key)
            if row["gtin"] not in price_map:
                price_map[row["gtin"]] = {}
            price_map[row["gtin"]][row["store"]] = row

    def get_name(product_join: dict, lang: str) -> str:
        if not product_join:
            return "Unknown"
        return (
            product_join.get(f"name_{lang}")
            or product_join.get("name_en")
            or "Unknown"
        )

    # Calculate totals per store
    store_totals: Dict[str, float] = {s: 0.0 for s in PUBLIC_STORES}
    store_missing: Dict[str, List[str]] = {s: [] for s in PUBLIC_STORES}
    item_breakdown = []

    for item in req.items:
        gtin = item.gtin
        qty = item.quantity
        item_prices = {}

        for store in PUBLIC_STORES:
            row = price_map.get(gtin, {}).get(store)
            if row:
                line_total = round(row["price_chf"] * qty, 2)
                store_totals[store] = round(store_totals[store] + line_total, 2)
                item_prices[store] = {
                    "price_chf":      row["price_chf"],
                    "line_total_chf": line_total,
                    "is_promotion":   row["is_promotion"],
                    "discount_pct":   row["discount_pct"],
                }
            else:
                store_missing[store].append(gtin)

        product_join = price_map.get(gtin, {})
        first_store = next(iter(product_join.values()), {})
        product_data = first_store.get("products") or {}

        item_breakdown.append({
            "gtin":     gtin,
            "name":     get_name(product_data, req.lang),
            "quantity": qty,
            "prices":   item_prices,
        })

    # Find cheapest store that has ALL items
    complete_stores = {
        s: t for s, t in store_totals.items()
        if not store_missing[s]
    }

    cheapest_complete = (
        min(complete_stores, key=complete_stores.get)
        if complete_stores else None
    )

    # Round all totals
    store_totals = {s: round(t, 2) for s, t in store_totals.items()}

    return {
        "items_count":       len(req.items),
        "store_totals_chf":  store_totals,
        "cheapest_complete_store": cheapest_complete,
        "cheapest_complete_total": complete_stores.get(cheapest_complete) if cheapest_complete else None,
        "store_missing_items":     {s: v for s, v in store_missing.items() if v},
        "item_breakdown":    item_breakdown,
    }
