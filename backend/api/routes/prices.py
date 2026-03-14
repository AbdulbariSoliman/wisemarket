# ============================================================
# WISEMARKET — PRICES ROUTES
# GET /prices/compare/{gtin}
# GET /prices/history/{gtin}
# ============================================================
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query

from backend.api.db import get_supabase_client

router = APIRouter()


@router.get("/compare/{gtin}")
def compare_prices(gtin: str):
    """
    Cross-store price comparison for a GTIN.
    Returns cheapest store, all store prices, price per 100g.
    Reads from store_price_snapshot view.
    """
    supabase = get_supabase_client()

    resp = (
        supabase.table("store_price_snapshot")
        .select("*")
        .eq("gtin", gtin)
        .order("snapshot_date", desc=True)
        .limit(1)
        .execute()
    )

    if not resp.data:
        raise HTTPException(status_code=404, detail=f"No price data for GTIN {gtin}")

    s = resp.data[0]
    return {
        "gtin":                  gtin,
        "snapshot_date":         str(s.get("snapshot_date")),
        "prices_chf":            s.get("prices_chf"),
        "prices_per_100g":       s.get("prices_per_100g"),
        "cheapest_store":        s.get("cheapest_store"),
        "cheapest_price_chf":    s.get("cheapest_price"),
        "most_expensive_store":  s.get("most_expensive_store"),
        "most_expensive_price":  s.get("most_expensive_price"),
        "price_spread_chf":      s.get("price_spread_chf"),
        "price_spread_pct":      s.get("price_spread_pct"),
        "stores_compared":       s.get("stores_compared"),
    }


@router.get("/history/{gtin}")
def price_history(
    gtin: str,
    store: Optional[str] = Query(None, description="Filter by store"),
    days: int = Query(30, ge=7, le=365, description="Number of days of history"),
):
    """
    Price history for a GTIN.
    Returns daily snapshots with direction signal.
    """
    supabase = get_supabase_client()

    query = (
        supabase.table("price_history")
        .select("gtin, store, price_chf, price_per_100g, is_promotion, discount_pct, price_date")
        .eq("gtin", gtin)
        .order("price_date", desc=True)
        .limit(days * 5)  # up to 5 stores * days
    )

    if store:
        query = query.eq("store", store.lower())

    resp = query.execute()

    if not resp.data:
        raise HTTPException(status_code=404, detail=f"No price history for GTIN {gtin}")

    # Group by store
    by_store: dict = {}
    for row in resp.data:
        s = row["store"]
        if s not in by_store:
            by_store[s] = []
        by_store[s].append({
            "date":          str(row["price_date"]),
            "price_chf":     row["price_chf"],
            "per_100g":      row["price_per_100g"],
            "is_promotion":  row["is_promotion"],
            "discount_pct":  row["discount_pct"],
        })

    return {
        "gtin":    gtin,
        "days":    days,
        "history": by_store,
    }


@router.get("/latest/{gtin}")
def latest_prices(gtin: str):
    """
    Latest price per store for a GTIN.
    """
    supabase = get_supabase_client()

    resp = (
        supabase.table("product_prices")
        .select(
            "gtin, store, price_chf, price_per_100g, price_per_pack_unit, "
            "is_promotion, discount_pct, promotion_label, promotion_ends, "
            "pack_size_raw, unit_quantity, unit_type, price_date"
        )
        .eq("gtin", gtin)
        .order("price_date", desc=True)
        .limit(10)
        .execute()
    )

    if not resp.data:
        raise HTTPException(status_code=404, detail=f"No prices found for GTIN {gtin}")

    # Deduplicate — keep latest per store
    seen_stores = set()
    latest = []
    for row in resp.data:
        if row["store"] not in seen_stores:
            seen_stores.add(row["store"])
            latest.append({
                "store":              row["store"],
                "price_chf":          row["price_chf"],
                "price_per_100g":     row["price_per_100g"],
                "price_per_pack_unit":row["price_per_pack_unit"],
                "is_promotion":       row["is_promotion"],
                "discount_pct":       row["discount_pct"],
                "promotion_label":    row["promotion_label"],
                "pack_size_raw":      row["pack_size_raw"],
                "unit_quantity":      row["unit_quantity"],
                "unit_type":          row["unit_type"],
                "price_date":         str(row["price_date"]),
            })

    return {"gtin": gtin, "prices": latest}
