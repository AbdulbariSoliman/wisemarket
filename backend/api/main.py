import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from backend.api.db import get_supabase_client
from backend.normalizer.ontology_loader import load_ontology
from backend.services.decision_engine import DecisionEngine
from backend.services.ingredient_parser import IngredientParser
from backend.services.ontology_matcher import OntologyMatcher
from backend.services.ontology_router import OntologyRouter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProductAnalysis(BaseModel):
    gtin: str
    store: Optional[str]
    name_en: Optional[str]
    category: str
    ingredients_raw: str
    ingredients_parsed: List[str]
    ontology_groups: List[str]
    matches: Dict[str, List[str]]
    verdicts: Dict[str, Any]


class ProductWarning(BaseModel):
    gtin: Optional[str]
    store: Optional[str]
    name_en: Optional[str]
    category: str
    ingredients_raw: str
    ingredients_parsed: List[str]
    warning: str


def _validate_gtin(gtin: str) -> None:
    if not gtin.isdigit() or len(gtin) not in (8, 13, 14):
        raise HTTPException(
            status_code=422,
            detail="Invalid GTIN format — must be 8, 13, or 14 digits",
        )


def _normalize_db_ingredients(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(x).strip().lower() for x in value if str(x).strip()]

    if isinstance(value, dict):
        for lang in ("en", "de", "fr", "it"):
            lang_value = value.get(lang)
            if isinstance(lang_value, list):
                return [str(x).strip().lower() for x in lang_value if str(x).strip()]

    return []


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

    logger.info("App shutdown — cleaning up state...")
    for attr in ("ontology_data", "parser", "router", "matcher", "decision_engine"):
        if hasattr(app.state, attr):
            delattr(app.state, attr)
    logger.info("Shutdown complete.")


app = FastAPI(
    title="Swiss Basket AI",
    version="1.0.0",
    description="Analyzes Swiss grocery products against ontology rules.",
    lifespan=lifespan,
)


@app.get("/")
def root():
    return {"message": "Swiss Basket AI API is running"}


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
def analyze_product(gtin: str):
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
    raw_ingredients = product.get("ingredients_raw") or ""
    category = product.get("category") or ""

    parsed_ingredients = _normalize_db_ingredients(product.get("ingredients_normalized"))

    if not parsed_ingredients:
        if not raw_ingredients.strip():
            return ProductWarning(
                gtin=product.get("gtin"),
                store=product.get("store"),
                name_en=product.get("name_en"),
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
        logger.exception("Routing failed for category '%s'", category)
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
    logger.info("Analyzed GTIN %s successfully in %.3fs", gtin, elapsed)

    return ProductAnalysis(
        gtin=product.get("gtin"),
        store=product.get("store"),
        name_en=product.get("name_en"),
        category=category,
        ingredients_raw=raw_ingredients,
        ingredients_parsed=parsed_ingredients,
        ontology_groups=groups,
        matches=matches,
        verdicts=verdicts,
    )