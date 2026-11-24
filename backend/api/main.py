# ============================================================
# WISEMARKET — MAIN API
# ============================================================
import logging
import os
import secrets
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Literal, Optional, Union

import httpx
import sentry_sdk
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from postgrest.exceptions import APIError
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from backend.api.db import DatabaseConfigError, get_supabase_client
from backend.config.stores import PUBLIC_STORES, STORES
from backend.normalizer.ontology_loader import load_ontology
from backend.services.decision_engine import DecisionEngine
from backend.services.ingredient_parser import IngredientParser
from backend.services.ontology_matcher import OntologyMatcher
from backend.services.ontology_router import OntologyRouter

load_dotenv()

# ── Logging ──────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Sentry ───────────────────────────────────────────────────
sentry_dsn = os.environ.get("SENTRY_DSN")
if sentry_dsn:
    sentry_sdk.init(dsn=sentry_dsn, traces_sample_rate=0.1)
    logger.info("Sentry enabled")

# ── Rate limiter ─────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)


# ── Auth ─────────────────────────────────────────────────────
def verify_admin_key(x_admin_key: Optional[str] = Header(None)):
    correct_key = os.environ.get("ADMIN_API_KEY", "")
    if not x_admin_key or not secrets.compare_digest(x_admin_key, correct_key):
        raise HTTPException(status_code=403, detail="Unauthorized")


# ── Response models ──────────────────────────────────────────
class PriceInfo(BaseModel):
    amount: Optional[float] = None
    currency: Optional[str] = None
    price_per_100g: Optional[float] = None
    price_per_pack_unit: Optional[float] = None
    is_promotion: Optional[bool] = None
    discount_pct: Optional[float] = None
    promotion_label: Optional[str] = None
    price_date: Optional[str] = None


class ProductAnalysis(BaseModel):
    gtin: str
    store: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    price: Optional[PriceInfo] = None
    ingredients_raw: str
    ingredients_parsed: List[str]
    ontology_groups: List[str]
    matches: Dict[str, List[str]]
    verdicts: Dict[str, Any]


class ProductWarning(BaseModel):
    gtin: Optional[str] = None
    store: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    ingredients_raw: str
    ingredients_parsed: List[str]
    warning: str


# ── Helpers ──────────────────────────────────────────────────
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
        for key in (lang, "en", "de", "fr", "it"):
            v = value.get(key)
            if isinstance(v, list):
                return [str(x).strip().lower() for x in v if str(x).strip()]
    return []


def _get_product_name(product: Dict, lang: str) -> Optional[str]:
    return (
        product.get(f"name_{lang}")
        or product.get("name_en")
        or product.get("name_de")
        or product.get("name_fr")
        or product.get("name_it")
    )


# ── Lifespan ─────────────────────────────────────────────────
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
    logger.info("Shutdown complete.")


# ── App ───────────────────────────────────────────────────────
app = FastAPI(
    title="WiseMarket",
    version="2.0.0",
    description="Switzerland's smartest shopping assistant.",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ─────────────────────────────────────────────────────
# Comma-separated list of allowed frontend origins, e.g.
# CORS_ORIGINS=https://wisemarket.vercel.app,http://localhost:5173
CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "CORS_ORIGINS", "http://localhost:5173,http://localhost:4173"
    ).split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ── Database error handling (applies to every route) ─────────
@app.exception_handler(DatabaseConfigError)
@app.exception_handler(httpx.HTTPError)
@app.exception_handler(ConnectionError)
async def database_unavailable_handler(request: Request, exc: Exception):
    logger.error("Database unavailable on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=503, content={"detail": "Database unavailable"})


@app.exception_handler(APIError)
async def database_query_error_handler(request: Request, exc: APIError):
    logger.error("Database query failed on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=502, content={"detail": "Database query failed"})

# ── Import and register route modules ────────────────────────
from backend.api.routes import products, prices, promotions, basket, scan, agent  # noqa: E402
app.include_router(products.router,   prefix="/products",   tags=["products"])
app.include_router(prices.router,     prefix="/prices",     tags=["prices"])
app.include_router(promotions.router, prefix="/promotions", tags=["promotions"])
app.include_router(basket.router,     prefix="/basket",     tags=["basket"])
app.include_router(scan.router,       prefix="/scan",       tags=["scan"])
app.include_router(agent.router,      prefix="/agent",      tags=["agent"])


# ── Public routes ─────────────────────────────────────────────
@app.get("/")
def root():
    return {"message": "WiseMarket API v2 is running"}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "2.0.0",
        "public_stores": PUBLIC_STORES,
        "services": {
            "ontology":        hasattr(app.state, "ontology_data"),
            "parser":          hasattr(app.state, "parser"),
            "router":          hasattr(app.state, "router"),
            "matcher":         hasattr(app.state, "matcher"),
            "decision_engine": hasattr(app.state, "decision_engine"),
        },
    }


@app.get("/analyze/{gtin}", response_model=Union[ProductAnalysis, ProductWarning])
@limiter.limit("60/minute")
def analyze_product(
    request: Request,
    gtin: str,
    lang: Literal["en", "de", "fr", "it"] = "en",
    store: Optional[str] = None,
):
    start = time.perf_counter()
    _validate_gtin(gtin)

    try:
        supabase = get_supabase_client()
        query = supabase.table("products").select("*").eq("gtin", gtin)
        if store:
            query = query.eq("store", store.lower())
        resp = query.limit(1).execute()
    except Exception as e:
        logger.exception("Database error for GTIN %s", gtin)
        raise HTTPException(status_code=503, detail="Database unavailable") from e

    if not resp.data:
        raise HTTPException(status_code=404, detail=f"Product {gtin} not found")

    product = resp.data[0]

    if product.get("store", "").lower() not in PUBLIC_STORES:
        raise HTTPException(status_code=403, detail="Product store not yet public")

    raw_ingredients = product.get("ingredients_raw") or ""
    category        = product.get("category") or ""
    name            = _get_product_name(product, lang)

    # ── Fetch latest price ────────────────────────────────────
    price_info = None
    try:
        price_resp = (
            supabase.table("product_prices")
            .select("price_chf, currency, price_per_100g, price_per_pack_unit, is_promotion, discount_pct, promotion_label, price_date")
            .eq("product_id", product.get("id"))
            .order("price_date", desc=True)
            .limit(1)
            .execute()
        )
        if price_resp.data:
            p = price_resp.data[0]
            price_info = PriceInfo(
                amount=p.get("price_chf"),
                currency=p.get("currency"),
                price_per_100g=p.get("price_per_100g"),
                price_per_pack_unit=p.get("price_per_pack_unit"),
                is_promotion=p.get("is_promotion"),
                discount_pct=p.get("discount_pct"),
                promotion_label=p.get("promotion_label"),
                price_date=str(p.get("price_date")) if p.get("price_date") else None,
            )
    except Exception as e:
        logger.warning("Price fetch failed for GTIN %s: %s", gtin, e)

    # ── Parse ingredients ─────────────────────────────────────
    parsed_ingredients = _normalize_db_ingredients(
        product.get("ingredients_normalized"), lang=lang
    )
    if not parsed_ingredients and raw_ingredients.strip():
        try:
            parsed_ingredients = app.state.parser.normalize(raw_ingredients)
        except Exception as e:
            logger.exception("Parsing failed for GTIN %s", gtin)
            raise HTTPException(status_code=500, detail="Ingredient parsing failed") from e

    if not parsed_ingredients and not raw_ingredients.strip():
        return ProductWarning(
            gtin=product.get("gtin"),
            store=product.get("store"),
            name=name,
            category=category,
            ingredients_raw="",
            ingredients_parsed=[],
            warning="No ingredients available for this product",
        )

    # ── Ontology pipeline ─────────────────────────────────────
    try:
        groups  = app.state.router.route(category)
        matches = app.state.matcher.match(parsed_ingredients, groups)
        if name and "halal" in str(name).lower() and not matches.get("halal_labels"):
            matches["halal_labels"] = ["halal (product name)"]
        verdicts = app.state.decision_engine.evaluate(matches, lang=lang)
    except Exception as e:
        logger.exception("Ontology pipeline failed for GTIN %s", gtin)
        raise HTTPException(status_code=500, detail="Analysis failed") from e

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


# ── Admin routes ──────────────────────────────────────────────
@app.get("/admin/stats", dependencies=[Depends(verify_admin_key)])
def admin_stats():
    return {
        "status": "ok",
        "stores": STORES,
        "public_stores": PUBLIC_STORES,
        "services": {
            "ontology":        hasattr(app.state, "ontology_data"),
            "parser":          hasattr(app.state, "parser"),
            "router":          hasattr(app.state, "router"),
            "matcher":         hasattr(app.state, "matcher"),
            "decision_engine": hasattr(app.state, "decision_engine"),
        },
    }


@app.get("/admin/health", dependencies=[Depends(verify_admin_key)])
def admin_health():
    return {
        "status": "ok",
        "version": "2.0.0",
        "public_stores": PUBLIC_STORES,
        "ontology_loaded":  hasattr(app.state, "ontology_data"),
        "sentry_enabled":   bool(os.environ.get("SENTRY_DSN")),
        "admin_key_set":    bool(os.environ.get("ADMIN_API_KEY")),
    }
