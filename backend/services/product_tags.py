# ============================================================
# WISEMARKET — STORED PRODUCT TAGS
# ============================================================
# Computes the `ontology_tags` JSON stored on each product, which the
# search filters use (/products/search?vegan=true, ...).
#
# It runs the SAME pipeline as /analyze/{gtin}:
#   IngredientParser -> OntologyRouter -> OntologyMatcher -> DecisionEngine
# so search results and product pages always agree.
# ============================================================
from functools import lru_cache
from typing import Dict, Optional

from backend.normalizer.ontology_loader import load_ontology
from backend.services.decision_engine import DecisionEngine
from backend.services.ingredient_parser import IngredientParser
from backend.services.ontology_matcher import OntologyMatcher
from backend.services.ontology_router import OntologyRouter


_DAIRY_WORDS = (
    "lait", "milk", "milch", "latte", "beurre", "butter", "burro", "crème", "cream",
    "sahne", "rahm", "fromage", "cheese", "käse", "formaggio", "lactos", "lattosio",
    "whey", "molke", "lactosérum", "siero", "casein", "kasein", "caséin", "casein",
    "yaourt", "yogurt", "yoghurt", "joghurt", "panna", "ghee", "babeurre", "curd",
    "mascarpone", "mozzarella", "ricotta", "quark", "séré", "skyr", "kefir", "kéfir",
    "parmesan", "parmigiano", "grana padano", "cheddar", "feta", "emmental", "gruyère",
    "greyerzer", "sbrinz", "tilsiter", "appenzeller", "raclette", "gorgonzola",
)


@lru_cache(maxsize=1)
def _pipeline():
    return IngredientParser(), OntologyRouter(), OntologyMatcher(load_ontology()), DecisionEngine()


def tags_from_ingredients(ingredients_raw: str, category: Optional[str] = None,
                          name: Optional[str] = None) -> Optional[Dict[str, bool]]:
    """
    Tags for the search filters, derived from the ingredient list.
    Returns None when there are no ingredients (the caller keeps its fallback).

    Search-filter meaning:
      vegan        -> no animal ingredient found: milk, egg, honey, meat,
                      fish, gelatine ... (traces ignored)
      vegetarian   -> no meat, fish, gelatine or lard found
      halal        -> no pork or alcohol, and meat/gelatine only with a halal
                      label (in the ingredients or the product name)
      gluten_free  -> no gluten grain found (traces count)
      lactose_free -> no milk ingredient found, or labelled lactose-free
      palm_oil     -> palm oil found
    """
    if not ingredients_raw or not ingredients_raw.strip():
        return None

    parser, router, matcher, engine = _pipeline()
    parsed = parser.normalize(ingredients_raw)
    if not parsed:
        return None

    matches = matcher.match(parsed, router.route(category or ""))
    if name and "halal" in name.lower() and not matches.get("halal_labels"):
        matches["halal_labels"] = ["halal (product name)"]
    v = engine.evaluate(matches)

    dairy_hits = [h for h in matches.get("animal_products", [])
                  if any(w in h for w in _DAIRY_WORDS)]

    return {
        "vegan":        bool(v["vegan"] or v["vegan_likely"]),
        "vegetarian":   bool(v["vegetarian"]),
        "halal":        bool(v["halal"]),
        "gluten_free":  not matches.get("coeliac_triggers"),
        "lactose_free": bool(v["is_lactose_free"]) or not dairy_hits,
        "palm_oil":     bool(v["has_palm_oil"]),
    }
