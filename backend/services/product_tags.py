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


# ── Products without an ingredient list (e.g. Migros) ────────────────
_VEGAN_NAME = re.compile(r"\b(vegan(e|er|es|o|a|i)?|végétalien(ne)?|plant[- ]based|pflanzlich(e|er|es)?)\b")
_VEGETARIAN_NAME = re.compile(r"\b(vegetarisch(e|er|es)?|végétarien(ne)?|vegetarian[oa]?|vegi|veggie)\b")
_GLUTEN_FREE_NAME = re.compile(r"gluten[- ]?fre[ie]|sans gluten|senza glutine|gluten[- ]free")
_LACTOSE_FREE_NAME = re.compile(r"lakto[s]?e[- ]?frei|laktosefrei|sans lactose|senza lattosio|lactose[- ]free")
_GLUTEN_NAME_WORDS = (
    "brot", "pasta", "mehl", "weizen", "gerste", "dinkel", "roggen", "nudeln", "kuchen",
    "gebäck", "teig", "biscuit", "cookie", "keks", "guetzli", "petit beurre", "croissant",
    "pizza", "spaghetti", "penne", "fusilli", "lasagne", "couscous", "paniert", "zwieback",
    "waffel", "cracker", "pain", "farine", "blé", "pâtes", "pane", "farina", "biscotti",
)
_EGG_NAME = re.compile(r"\b(eggs?|oeufs?|œufs?|eier|ei|uova|uovo)\b")
_MEAT_FISH_CATEGORIES = {"meat", "fish"}
_ANIMAL_CATEGORIES = {"meat", "fish", "dairy"}


def tags_from_name(name: Optional[str], category: Optional[str] = None) -> Dict[str, Optional[bool]]:
    """
    Tags for a product we only know by its name and category.

    A name can prove that something is NOT vegan ("au Lait", "Butter"),
    but it can't prove that it IS vegan: the missing ingredient list might
    contain anything. So the answer is False when there is evidence against,
    True only when the name itself says so ("vegan", "glutenfrei", "Halal"),
    and None (unknown) otherwise. The app shows no badge for None.
    """
    low = (name or "").lower()
    cat = (category or "").lower()
    tags: Dict[str, Optional[bool]] = {
        "vegan": None, "vegetarian": None, "halal": None,
        "gluten_free": None, "lactose_free": None, "palm_oil": None,
    }
    if not low:
        return tags

    parser, router, matcher, _ = _pipeline()
    matches = matcher.match(parser.normalize(low), router.route(cat))
    matches = apply_name_hints(matches, name)

    animal = bool(matches.get("animal_products") or matches.get("egg_synonyms"))
    meat_words = bool(matches.get("meat") or matches.get("pork") or matches.get("fish_synonyms")
                      or matches.get("shellfish_synonyms"))
    # Some sources file eggs under "meat" ("chicken-eggs"): an egg name with
    # no meat word is not meat, whatever the category says.
    is_egg = (bool(matches.get("egg_synonyms")) or bool(_EGG_NAME.search(low))) and not meat_words
    meat_fish = meat_words or (cat in _MEAT_FISH_CATEGORIES and not is_egg)
    dairy = any(any(w in h for w in _DAIRY_WORDS) for h in matches.get("animal_products", []))
    says_vegan = bool(_VEGAN_NAME.search(low))
    says_vegetarian = bool(_VEGETARIAN_NAME.search(low))

    # vegan / vegetarian. "Vegane Bratwurst" or "Planted Chicken vegan" name
    # a meat on purpose: the label wins over the meat word.
    if says_vegan:
        tags["vegan"] = tags["vegetarian"] = True
        meat_fish = False
    elif says_vegetarian:
        tags["vegetarian"] = True
        tags["vegan"] = False if (animal or dairy) else None
        meat_fish = False
    elif meat_fish:
        tags["vegan"] = tags["vegetarian"] = False
    elif animal or cat in _ANIMAL_CATEGORIES:
        tags["vegan"] = False

    # halal: pork or alcohol rules it out; only a halal label proves it
    if matches.get("alcohol") or (matches.get("pork") and not says_vegan):
        tags["halal"] = False
    elif matches.get("halal_labels"):
        tags["halal"] = True
    elif meat_fish and cat == "meat" and not matches.get("fish_synonyms") and not is_egg:
        tags["halal"] = False

    # gluten
    if _GLUTEN_FREE_NAME.search(low):
        tags["gluten_free"] = True
    elif matches.get("coeliac_triggers") or any(w in low for w in _GLUTEN_NAME_WORDS):
        tags["gluten_free"] = False

    # lactose
    if _LACTOSE_FREE_NAME.search(low):
        tags["lactose_free"] = True
    elif dairy:
        tags["lactose_free"] = False

    if matches.get("palm_oil"):
        tags["palm_oil"] = True

    # Plain fruit and vegetables are vegan, halal, gluten- and lactose-free
    # by nature, as long as the name shows nothing else in them.
    if cat == "fresh_produce" and all(v is None for v in tags.values()):
        tags.update(vegan=True, vegetarian=True, halal=True, gluten_free=True, lactose_free=True)
    return tags
