import logging
import os
import secrets
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Literal, Optional, Union

import sentry_sdk
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from backend.api.db import get_supabase_client
from backend.config.stores import PUBLIC_STORES, STORES
from backend.normalizer.ontology_loader import load_ontology
from backend.services.decision_engine import DecisionEngine
from backend.services.ingredient_parser import IngredientParser
from backend.services.ontology_matcher import OntologyMatcher
from backend.services.ontology_router import OntologyRouter

# --- Sentry ---
sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN"),
    traces_sample_rate=0.2,
    send_default_pii=False,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Rate Limiter ---
limiter = Limiter(key_func=get_remote_address)


# --- Admin Auth ---
def verify_admin_key(x_admin_key: str = Header(...)):
    """
    Protects admin routes with a secret key.
    Uses constant-time comparison to prevent timing attacks.
    Zero DB calls — pure in-memory check.
    """
    correct_key = os.environ.get("ADMIN_API_KEY", "")
    if not x_admin_key or not secrets.compare_digest(x_admin_key, correct_key):
        raise HTTPException(status_code=403, detail="Unauthorized")


# --- Response Models ---
class PriceInfo(BaseModel):
    amount: Optional[float]
    currency: Optional[str]
    unit_price: Optional[float]
    price_date: Optional[str]
    promotion_info: Optional[Dict]


class ProductAnalysis(BaseModel):
    gtin: str
    store: Optional[str]
    name: Optional[str]
    category: str
    price: Optional[PriceInfo]
    ingredients_raw: str
    ingredients_parsed: List[str]
    ontology_groups: List[str]
    matches: Dict[str, List[str]]
    verdicts: Dict[str, Any]


class ProductWarning(BaseModel):
    gtin: Optional[str]
    store: Optional[str]
    name: Optional[str]
    category: str
    ingredients_raw: str
    ingredients_parsed: List[str]
    warning: str


# --- Helpers ---
def _validate_gtin(gtin: str) -> None:
    if not gtin.isdigit() or len(gtin) not in (8, 13, 14):
        raise HTTPException(
            status_code=422,
            detail="Invalid GTIN format - must be 8, 13, or 14 digits",
        )


def _normalize_db_ingredients(value: Any, lang: str = "en") -> List[str]:
    if isinstance(value, list):
        return [str(x).strip().lower() for x in value if str(x).strip()]
    if isinstance(value, dict):
        lang_value = value.get(lang)
        if isinstance(lang_value, list):
            return [str(x).strip().lower() for x in lang_value if str(x).strip()]
        for fallback in ("en", "de", "fr", "it"):
            fallback_value = value.get(fallback)
            if isinstance(fallback_value, list):
                return [str(x).strip().lower() for x in fallback_value if str(x).strip()]
    return []


def _get_product_name(product: Dict, lang: str) -> Optional[str]:
    return (
        product.get(f"name_{lang}")
        or product.get("name_en")
        or product.get("name_de")
        or product.get("name_fr")
        or product.get("name_it")
    )


# --- Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Loading ontology and services...")
    try:
        ontology_data = load_ontology()
        app.state.ontology_data = ontology_data
        app.state.parser = IngredientParser()
        app.state.router = OntologyRouter()
        app.state.matcher = OntologyMatcher(ontology_data)
        app.state.decision_engine = DecisionEngine()
        logger.info("All services loaded successfully.")
    except Exception as e:
        logger.exception("Startup failed")
        raise RuntimeError(f"Startup failed: {e}") from e
    yield
    logger.info("App shutdown - cleaning up state...")
    for attr in ("ontology_data", "parser", "router", "matcher", "decision_engine"):
        if hasattr(app.state, attr):
            delattr(app.state, attr)
    logger.info("Shutdown complete.")


# --- App ---
app = FastAPI(
    title="WiseMarket",
    version="1.0.0",
    description="Switzerland's smartest shopping assistant.",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ================================
# PUBLIC ROUTES — no auth needed
# ================================

@app.get("/")
def root():
    return {"message": "WiseMarket API is running"}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "services": {
            "ontology_data": hasattr(app.state, "ontology_data"),
            "parser": hasattr(app.state, "parser"),
            "router": hasattr(app.state, "router"),
            "matcher": hasattr(app.state, "matcher"),
            "decision_engine": hasattr(app.state, "decision_engine"),
        },
    }


@app.get("/analyze/{gtin}", response_model=Union[ProductAnalysis, ProductWarning])
@limiter.limit("60/minute")
def analyze_product(
    request: Request,
    gtin: str,
    lang: Literal["en", "de", "fr", "it"] = "en",
):
    start = time.perf_counter()
    _validate_gtin(gtin)

    try:
        supabase = get_supabase_client()
        resp = (
            supabase.table("products_new")
            .select("*")
            .eq("gtin", gtin)
            .limit(1)
            .execute()
        )
    except Exception as e:
        logger.exception("Database error for GTIN %s", gtin)
        raise HTTPException(status_code=503, detail="Database unavailable") from e

    if not resp.data:
        raise HTTPException(status_code=404, detail=f"Product with GTIN {gtin} not found")

    product = resp.data[0]

    store = product.get("store", "").lower()
    if store not in PUBLIC_STORES:
        raise HTTPException(status_code=403, detail="This product is not available yet")

    raw_ingredients = product.get("ingredients_raw") or ""
    category = product.get("category") or ""
    name = _get_product_name(product, lang)

    price_info = None
    try:
        price_resp = (
            supabase.table("product_prices")
            .select("*")
            .eq("product_id", product.get("id"))
            .order("price_date", desc=True)
            .limit(1)
            .execute()
        )
        if price_resp.data:
            p = price_resp.data[0]
            price_info = PriceInfo(
                amount=p.get("price"),
                currency=p.get("currency"),
                unit_price=p.get("unit_price"),
                price_date=p.get("price_date"),
                promotion_info=p.get("promotion_info"),
            )
    except Exception as e:
        logger.warning("Price fetch failed for GTIN %s: %s", gtin, e)

    parsed_ingredients = _normalize_db_ingredients(
        product.get("ingredients_normalized"), lang=lang
    )

    if not parsed_ingredients:
        if not raw_ingredients.strip():
            return ProductWarning(
                gtin=product.get("gtin"),
                store=product.get("store"),
                name=name,
                category=category,
                ingredients_raw="",
                ingredients_parsed=[],
                warning="No ingredients available for this product",
            )
        try:
            parsed_ingredients = app.state.parser.normalize(raw_ingredients)
        except Exception as e:
            logger.exception("Parsing failed for GTIN %s", gtin)
            raise HTTPException(status_code=500, detail="Ingredient parsing failed") from e

    try:
        groups = app.state.router.route(category)
    except Exception as e:
        logger.exception("Routing failed for category %s", category)
        raise HTTPException(status_code=500, detail="Ontology routing failed") from e

    try:
        matches = app.state.matcher.match(parsed_ingredients, groups)
    except Exception as e:
        logger.exception("Matching failed for GTIN %s", gtin)
        raise HTTPException(status_code=500, detail="Ontology matching failed") from e

    try:
        verdicts = app.state.decision_engine.evaluate(matches)
    except Exception as e:
        logger.exception("Decision engine failed for GTIN %s", gtin)
        raise HTTPException(status_code=500, detail="Decision evaluation failed") from e

    elapsed = time.perf_counter() - start
    logger.info("Analyzed GTIN %s in %.3fs", gtin, elapsed)

    return ProductAnalysis(
        gtin=product.get("gtin"),
        store=product.get("store"),
        name=name,
        category=category,
        price=price_info,
        ingredients_raw=raw_ingredients,
        ingredients_parsed=parsed_ingredients,
        ontology_groups=groups,
        matches=matches,
        verdicts=verdicts,
    )


# ================================
# ADMIN ROUTES — API key required
# ================================

@app.get("/admin/stats", dependencies=[Depends(verify_admin_key)])
def admin_stats():
    """
    Returns store stats and system status.
    Requires X-Admin-Key header.
    """
    return {
        "status": "ok",
        "stores": STORES,
        "public_stores": PUBLIC_STORES,
        "services": {
            "ontology_data": hasattr(app.state, "ontology_data"),
            "parser": hasattr(app.state, "parser"),
            "router": hasattr(app.state, "router"),
            "matcher": hasattr(app.state, "matcher"),
            "decision_engine": hasattr(app.state, "decision_engine"),
        },
    }


@app.get("/admin/health", dependencies=[Depends(verify_admin_key)])
def admin_health():
    """
    Detailed health check for admin.
    Requires X-Admin-Key header.
    """
    return {
        "status": "ok",
        "version": "1.0.0",
        "public_stores": PUBLIC_STORES,
        "ontology_loaded": hasattr(app.state, "ontology_data"),
        "sentry_enabled": bool(os.environ.get("SENTRY_DSN")),
        "admin_key_set": bool(os.environ.get("ADMIN_API_KEY")),
    }
