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
import re
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


_ALCOHOL_NAME = re.compile(
    r"\b(bier|beer|bière|biere|birra|lager|wein|wine|vin|vino|prosecco|champagne|"
    r"cidre|cider|sidro|whisky|whiskey|vodka|rum|rhum|gin|likör|liqueur|liquore)\b")
_ALCOHOL_FREE_NAME = re.compile(
    r"alkoholfrei|sans alcool|alcohol[- ]free|non[- ]alcoholic|analcolic|senza alcol|"
    r"\b0[.,]0\b|ginger|ingwer|root beer")


def apply_name_hints(matches: Dict[str, list], name: Optional[str]) -> Dict[str, list]:
    """Use the product name when the ingredient list is silent:
    "Halal Chicken Breast" -> halal label, "Appenzeller Bier" -> alcohol."""
    if not name:
        return matches
    low = str(name).lower()
    if "halal" in low and not matches.get("halal_labels"):
        matches["halal_labels"] = ["halal (product name)"]
    if (_ALCOHOL_NAME.search(low) and not _ALCOHOL_FREE_NAME.search(low)
            and not matches.get("alcohol")):
        matches["alcohol"] = [f"{low} (product name)"]
    return matches


# Very common ingredient-list words in the four supported languages. If an
# ingredient list contains none of them AND no ontology term matched, it is
# probably in another language (e.g. Croatian) and we can't judge it.
_COMMON_WORDS = {
    "and", "with", "sugar", "salt", "water", "flour", "oil", "milk", "wheat", "natural",
    "und", "mit", "zucker", "salz", "wasser", "mehl", "öl", "milch", "aus", "natürliches",
    "et", "de", "du", "des", "avec", "sucre", "sel", "eau", "farine", "huile", "lait",
    "di", "con", "zucchero", "sale", "acqua", "farina", "olio", "latte", "naturale",
}


# Very common ingredient words in languages the ontology does NOT cover
# (Spanish, Portuguese, Dutch, Nordic, Slavic, Turkish ...).
_FOREIGN_WORDS = {
    "leche", "harina", "azúcar", "azucar", "trigo", "aceite", "manteca", "huevo", "cebada",
    "suero", "jarabe", "grasa", "agua", "y", "leite", "farinha", "açúcar", "óleo", "oleo",
    "peixe", "ovo", "ovos", "água", "em", "sardinhas", "suiker", "tarwebloem", "melk",
    "ingrediënten", "socker", "sukker", "mjölk", "mælk", "vetemjöl", "hvedemel", "cukr",
    "mléko", "cukier", "mleko", "mąka", "skład", "složení", "šećer", "mlijeko", "brašno",
    "şeker", "süt", "cukor", "tej", "liszt",
}
# Letters that do not occur in English, German, French or Italian
_FOREIGN_LETTERS = set("ñãõčřěůłąęśźżőűşğıđćšžåøæ")

_GERMAN_ENDINGS = ("öl", "mehl", "zucker", "salz", "milch", "wasser", "pulver", "extrakt")


def _looks_supported(ingredients_raw: str, matches: Dict[str, list]) -> bool:
    """True if the list looks like English, German, French or Italian."""
    words = set(re.findall(r"[^\W\d_]+", ingredients_raw.lower()))
    foreign = len(words & _FOREIGN_WORDS) + sum(1 for w in words if set(w) & _FOREIGN_LETTERS)
    if foreign >= 2 and foreign >= len(words & _COMMON_WORDS):
        return False
    if words & _COMMON_WORDS:
        return True
    if any(w.endswith(_GERMAN_ENDINGS) for w in words):
        return True
    # a match in any group except the (very short, multi-language) allergen list
    return any(v for g, v in matches.items() if g != "allergens")


@lru_cache(maxsize=1)
def _pipeline():
    return IngredientParser(), OntologyRouter(), OntologyMatcher(load_ontology()), DecisionEngine()


def tags_from_ingredients(ingredients_raw: str, category: Optional[str] = None,
                          name: Optional[str] = None) -> Optional[Dict[str, bool]]:
    """
    Tags for the search filters, derived from the ingredient list.
    Returns None when there are no ingredients, or when the list is in a
    language the ontology does not cover (the caller keeps its fallback).

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
    if not _looks_supported(ingredients_raw, matches):
        return None  # language not supported: keep the existing tags
    matches = apply_name_hints(matches, name)
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
