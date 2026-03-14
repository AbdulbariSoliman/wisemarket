# ============================================================
# WISEMARKET — SCAN ROUTES
# POST /scan
# ============================================================
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.api.db import get_supabase_client
from backend.config.stores import PUBLIC_STORES

router = APIRouter()


class ScanRequest(BaseModel):
    barcode: str
    store: Optional[str] = None
    user_id: Optional[str] = None
    lang: Literal["en", "de", "fr", "it"] = "en"


@router.post("")
def scan_barcode(req: ScanRequest):
    """
    Barcode scan endpoint.
    1. Normalise barcode via barcode_aliases (if exists)
    2. Look up product in products table
    3. Return product + latest prices + ontology_tags
    4. Log scan to user_scans if user_id provided
    """
    supabase = get_supabase_client()
    barcode = req.barcode.strip()

    # ── Step 1: normalise via barcode_aliases ─────────────────
    alias_resp = (
        supabase.table("barcode_aliases")
        .select("normalized_gtin")
        .eq("raw_barcode", barcode)
        .limit(1)
        .execute()
    )
    gtin = (
        alias_resp.data[0]["normalized_gtin"]
        if alias_resp.data
        else barcode
    )

    # ── Step 2: look up product ───────────────────────────────
    query = (
        supabase.table("products")
        .select("*")
        .eq("gtin", gtin)
        .eq("is_active", True)
        .in_("store", PUBLIC_STORES)
    )
    if req.store:
        query = query.eq("store", req.store.lower())

    prod_resp = query.execute()

    if not prod_resp.data:
        raise HTTPException(
            status_code=404,
            detail=f"Product not found for barcode {barcode}",
        )

    # ── Step 3: get latest prices ─────────────────────────────
    price_resp = (
        supabase.table("product_prices")
        .select(
            "store, price_chf, price_per_100g, is_promotion, "
            "discount_pct, promotion_label, price_date"
        )
        .eq("gtin", gtin)
        .in_("store", PUBLIC_STORES)
        .order("price_date", desc=True)
        .limit(10)
        .execute()
    )

    # Deduplicate — latest per store
    seen = set()
    prices = []
    for row in price_resp.data:
        if row["store"] not in seen:
            seen.add(row["store"])
            prices.append({
                "store":           row["store"],
                "price_chf":       row["price_chf"],
                "price_per_100g":  row["price_per_100g"],
                "is_promotion":    row["is_promotion"],
                "discount_pct":    row["discount_pct"],
                "promotion_label": row["promotion_label"],
                "price_date":      str(row["price_date"]),
            })

    # ── Step 4: format product results ───────────────────────
    lang = req.lang
    results = []
    for p in prod_resp.data:
        name = (
            p.get(f"name_{lang}")
            or p.get("name_en")
            or p.get("name_de")
        )
        results.append({
            "gtin":          p.get("gtin"),
            "store":         p.get("store"),
            "name":          name,
            "brand":         p.get("brand"),
            "category":      p.get("category"),
            "ontology_tags": p.get("ontology_tags"),
            "allergens":     p.get("allergens"),
            "nutrition":     p.get("nutrition_cache"),
            "pack_size_raw": p.get("pack_size_raw"),
            "image_url":     p.get("image_url"),
        })

    # ── Step 5: log scan ──────────────────────────────────────
    if req.user_id and results:
        first = results[0]
        try:
            supabase.table("user_scans").insert({
                "user_id":      req.user_id,
                "gtin":         gtin,
                "store":        req.store or first.get("store"),
                "product_name": first.get("name"),
                "lang":         lang,
                "verdicts":     first.get("ontology_tags"),
            }).execute()
        except Exception:
            pass  # scan logging failure should never block the response

    return {
        "barcode":   barcode,
        "gtin":      gtin,
        "products":  results,
        "prices":    prices,
    }
