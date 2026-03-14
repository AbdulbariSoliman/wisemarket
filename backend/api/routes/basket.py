# ============================================================
# WISEMARKET — BASKET ROUTES
# POST /basket/calculate
# ============================================================
from datetime import date
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


# ============================================================
# SHOPPING LIST PDF EXPORT
# POST /basket/export
# ============================================================
from fastapi import Response as FastAPIResponse
from backend.services.export_service import generate_shopping_list_pdf


class ExportRequest(BaseModel):
    items: List[BasketItem]
    store_filter: Optional[str] = None
    list_name: Optional[str] = None
    lang: Literal["en", "de", "fr", "it"] = "en"
    qr_url: Optional[str] = None


@router.post("/export")
def export_shopping_list(req: ExportRequest):
    """
    Export a shopping list as a multilingual PDF.
    Groups items by category (aisle order).
    Shows dietary badges, prices, totals.
    Highlights cheapest store.
    """
    if not req.items:
        raise HTTPException(status_code=422, detail="Basket is empty")

    supabase = get_supabase_client()
    gtins = [item.gtin for item in req.items]
    qty_map = {item.gtin: item.quantity for item in req.items}
    lang = req.lang

    # Fetch products
    prod_resp = (
        supabase.table("products")
        .select(
            "id, gtin, store, name_en, name_de, name_fr, name_it, "
            "brand, category, ontology_tags, pack_size_raw"
        )
        .in_("gtin", gtins)
        .in_("store", PUBLIC_STORES)
        .execute()
    )

    # Fetch latest prices
    price_resp = (
        supabase.table("product_prices")
        .select("product_id, gtin, store, price_chf, price_per_100g, is_promotion")
        .in_("gtin", gtins)
        .in_("store", PUBLIC_STORES)
        .order("price_date", desc=True)
        .execute()
    )

    # Build price map: {(gtin, store): price_chf}
    price_map: Dict = {}
    seen_prices = set()
    for row in price_resp.data:
        key = (row["gtin"], row["store"])
        if key not in seen_prices:
            seen_prices.add(key)
            price_map[key] = row["price_chf"]

    # Build product map: {(gtin, store): product_row}
    prod_map: Dict = {}
    for row in prod_resp.data:
        key = (row["gtin"], row["store"])
        prod_map[key] = row

    # Determine preferred store per item
    def best_store_for(gtin: str) -> tuple:
        """Returns (store, price) — cheapest available or first found"""
        candidates = [
            (s, p) for (g, s), p in price_map.items()
            if g == gtin and (not req.store_filter or s == req.store_filter.lower())
        ]
        if not candidates:
            return (req.store_filter or PUBLIC_STORES[0], None)
        return min(candidates, key=lambda x: x[1])

    # Assemble export items
    export_items = []
    store_totals: Dict[str, float] = {}

    for item in req.items:
        gtin = item.gtin
        qty = item.quantity
        store, price = best_store_for(gtin)

        prod = prod_map.get((gtin, store)) or {}
        name_key = f"name_{lang}" if lang in ("en", "de", "fr", "it") else "name_en"

        export_items.append({
            "gtin":          gtin,
            "name_en":       prod.get("name_en"),
            "name_de":       prod.get("name_de"),
            "name_fr":       prod.get("name_fr"),
            "name_it":       prod.get("name_it"),
            "brand":         prod.get("brand"),
            "category":      prod.get("category") or "other",
            "pack_size_raw": prod.get("pack_size_raw"),
            "store":         store,
            "quantity":      qty,
            "price_chf":     price,
            "ontology_tags": prod.get("ontology_tags") or {},
        })

        if price is not None:
            store_totals[store] = round(
                store_totals.get(store, 0) + price * qty, 2
            )

    # Find cheapest complete store
    cheapest = min(store_totals, key=store_totals.get) if store_totals else None

    # Generate PDF
    pdf_bytes = generate_shopping_list_pdf(
        items=export_items,
        lang=lang,
        store_filter=req.store_filter,
        list_name=req.list_name,
        cheapest_store=cheapest,
        basket_totals=store_totals if len(store_totals) > 1 else None,
        qr_url=req.qr_url,
    )

    filename = f"wisemarket_list_{lang}_{date.today().isoformat()}.pdf"

    return FastAPIResponse(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )
