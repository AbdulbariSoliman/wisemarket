import re
from typing import Dict, List, Pattern, Set, Tuple

from backend.services.ingredient_parser import TRACE_PATTERN


# Phrases that contain an animal / palm word but are NOT that ingredient.
# They are removed from an ingredient before matching the groups below.
PLANT_EXCEPTIONS = [
    # German words that contain a food word by accident ("Landwirtschaft" has "schaf")
    "landwirtschaft", "wirtschaft",
    # cocoa / nut / shea "butter"
    "cocoa butter", "beurre de cacao", "kakaobutter", "burro di cacao",
    "peanut butter", "beurre de cacahuète", "beurre de cacahuete", "erdnussbutter",
    "burro di arachidi", "shea butter", "beurre de karité", "sheabutter",
    "nut butter", "nussbutter", "almond butter", "mandelbutter",
    "beurre végétal", "beurre vegetal", "vegetable butter", "plant butter",
    "pflanzliche butter", "pflanzenbutter", "burro vegetale",
    # plant "milks" and creams
    "coconut milk", "lait de coco", "kokosmilch", "latte di cocco",
    "coconut cream", "crème de coco", "kokoscreme", "kokosnusscreme",
    "almond milk", "lait d'amande", "mandelmilch", "latte di mandorla",
    "oat milk", "lait d'avoine", "hafermilch", "latte d'avena",
    "soy milk", "soya milk", "lait de soja", "sojamilch", "latte di soia",
    "rice milk", "lait de riz", "reismilch", "latte di riso",
    # not dairy despite the name
    "milchsäure", "milchsaeure", "lactic acid", "acide lactique", "acido lattico",
    "cream of tartar", "crème de tartre", "honigmelone", "honeydew",
    # German "Eiweiß" also means protein in general: plant proteins are not egg
    "sojaeiweiß", "sojaeiweiss", "erbseneiweiß", "erbseneiweiss",
    "weizeneiweiß", "weizeneiweiss", "pflanzeneiweiß", "pflanzeneiweiss",
    "pflanzliches eiweiß", "pflanzliches eiweiss", "reiseiweiß", "reiseiweiss",
    # sugar alcohols (polyols) are not alcohol
    "zuckeralkohol", "zuckeralkohole", "sugar alcohol", "sugar alcohols",
    "polyalcool", "polyalcools", "alcool de sucre", "alcol di zucchero",
    # yogurt cultures / lactic ferments are bacteria, not dairy
    "joghurtkulturen", "joghurtkultur", "yoghurtkulturen", "yogurt cultures",
    "yoghurt cultures", "cultures de yaourt", "ferments de yaourt", "fermenti lattici",
    # vinegars made from spirit or cider (wine vinegar stays in the alcohol list)
    "vinaigre d'alcool", "spirit vinegar", "branntweinessig", "aceto di alcol",
    "cider vinegar", "apple cider vinegar", "vinaigre de cidre", "apfelessig", "aceto di mele",
    # palm SUGAR is not palm oil
    "sucre de palme", "sucre de fleur de coco", "palm sugar", "palmzucker", "zucchero di palma",
]

# "May contain traces of ..." statements: for allergen and gluten groups they
# still count (they matter to allergic / coeliac users); for diet groups such as
# vegan, vegetarian, halal or palm oil they are not ingredients and are ignored.
TRACE_RELEVANT_GROUPS = {
    "allergens", "coeliac_triggers", "nut_synonyms", "soy_synonyms",
    "sesame_synonyms", "mustard_synonyms",
}

# Animal NAMES used for dairy / eggs: "sheep's milk" or "Ziegenkäse" is not meat.
# Removed only for the meat / fish groups, so the milk still counts as dairy.
MEAT_GROUP_EXCEPTIONS = [
    "sheep's milk", "sheep milk", "goat's milk", "goat milk", "buffalo milk",
    "lait de brebis", "lait de chèvre", "lait de bufflonne", "fromage de brebis", "fromage de chèvre",
    "schafmilch", "ziegenmilch", "büffelmilch", "schafkäse", "ziegenkäse",
    "latte di pecora", "latte di capra", "latte di bufala", "formaggio di pecora", "formaggio di capra",
    "chicken egg", "hen's egg", "œuf de poule", "oeuf de poule", "hühnerei", "uovo di gallina",
]
MEAT_GROUPS = {"meat", "pork", "fish_synonyms", "shellfish_synonyms"}

# Groups where a hit means "the product CONTAINS this". For these groups,
# terms that are really claims of absence are ignored (see EXCLUDED_TERM_KEYS),
# and phrases preceded/followed by a negation ("sans", "ohne", "-free") are skipped.
PRESENCE_GROUPS = {
    "allergens", "animal_products", "meat", "pork", "fish_synonyms",
    "shellfish_synonyms", "egg_synonyms", "alcohol", "palm_oil", "caffeine",
    "coeliac_triggers", "nut_synonyms", "soy_synonyms", "sesame_synonyms",
    "mustard_synonyms", "sulphite_markers", "histamine_triggers",
    "artificial_sweeteners", "sugar_synonyms",
}

# Ontology rows inside presence groups that describe the ABSENCE of the
# ingredient, or that are too vague to count as presence.
EXCLUDED_TERM_KEYS = {
    "palm_oil": {"palm_free", "vegetable_fat"},
    "egg_synonyms": {"egg_free", "free_range_egg"},
}

NEGATION_BEFORE = re.compile(
    r"(?:\b(?:sans|ohne|without|no|senza|kein|keine|zéro|zero|free from|frei von)\s+(?:[\w']+\s+){0,3})$",
    re.IGNORECASE,
)
NEGATION_AFTER = re.compile(r"^\s*-?\s*(?:free|frei)\b", re.IGNORECASE)

# German compound words: "Vollmilchpulver" contains "milch". For German terms
# of at least this length, a match inside a longer word is accepted.
GERMAN_COMPOUND_MIN_LEN = 5


class OntologyMatcher:
    """
    Match normalized ingredient tokens against selected ontology groups.

    Version 2:
    - exact match of the whole ingredient (as in version 1), plus
    - phrase match inside a longer ingredient on whole words
      ("lait" in "lait écrémé en poudre"), plus
    - German compound match for longer German terms
      ("milch" in "vollmilchpulver"), while
    - ignoring plant-based look-alikes ("beurre de cacao", "lait de coco"),
    - ignoring negated phrases in presence groups ("sans huile de palme"),
    - ignoring absence/vague rows in presence groups (palm_free, vegetable_fat).
    Returns matched ingredient tokens per group (same shape as version 1).
    """

    def __init__(self, ontology_data: Dict[str, List[dict]]) -> None:
        self.ontology_index = self._build_index(ontology_data)
        self.phrase_index = self._build_phrase_index(ontology_data)
        self._exceptions = sorted({e.replace("œ", "oe") for e in PLANT_EXCEPTIONS},
                                  key=len, reverse=True)
        self._meat_exceptions = sorted({e.replace("œ", "oe") for e in MEAT_GROUP_EXCEPTIONS},
                                       key=len, reverse=True)

    # ── index building ─────────────────────────────────────────

    @staticmethod
    def _terms(row: dict, keys=("term", "en", "de", "fr", "it")) -> Set[str]:
        terms: Set[str] = set()
        for key in keys:
            value = row.get(key)
            if not value:
                continue
            for part in str(value).split(";"):
                token = part.strip().lower().replace("_", " ").replace("œ", "oe")
                if token:
                    terms.add(token)
        return terms

    def _build_index(self, ontology_data: Dict[str, List[dict]]) -> Dict[str, Set[str]]:
        index: Dict[str, Set[str]] = {}
        for group_name, rows in ontology_data.items():
            excluded = EXCLUDED_TERM_KEYS.get(group_name, set())
            terms: Set[str] = set()
            for row in rows:
                if row.get("term") in excluded:
                    continue
                terms |= self._terms(row)
            index[group_name] = terms
        return index

    def _build_phrase_index(
        self, ontology_data: Dict[str, List[dict]]
    ) -> Dict[str, List[Tuple[str, Pattern, bool]]]:
        """Per group: (phrase, compiled whole-word regex, allow_compound)."""
        index: Dict[str, List[Tuple[str, Pattern, bool]]] = {}
        for group_name, rows in ontology_data.items():
            excluded = EXCLUDED_TERM_KEYS.get(group_name, set())
            german: Set[str] = set()
            for row in rows:
                if row.get("term") in excluded:
                    continue
                german |= self._terms(row, keys=("de",))
            phrases = self.ontology_index.get(group_name, set())
            entries = []
            for phrase in sorted(phrases, key=len, reverse=True):
                if len(phrase) < 3:
                    continue  # too short to match safely inside other text
                # simple plurals: "maquereau" also matches "maquereaux"
                plural = r"(?:s|x|es)?" if len(phrase) >= 4 and phrase[-1].isalpha() else ""
                pattern = re.compile(r"(?<!\w)" + re.escape(phrase) + plural + r"(?!\w)")
                compound = (
                    phrase in german
                    and len(phrase) >= GERMAN_COMPOUND_MIN_LEN
                    and " " not in phrase
                )
                entries.append((phrase, pattern, compound))
            index[group_name] = entries
        return index

    # ── matching ───────────────────────────────────────────────

    def _strip_exceptions(self, text: str, group: str = "") -> str:
        phrases = self._exceptions
        if group in MEAT_GROUPS:
            phrases = self._meat_exceptions + self._exceptions
        for phrase in phrases:
            if phrase in text:
                text = text.replace(phrase, " ")
        return text

    @staticmethod
    def _negated(text: str, start: int, end: int) -> bool:
        return bool(NEGATION_BEFORE.search(text[:start]) or NEGATION_AFTER.match(text[end:]))

    def _phrase_hit(self, text: str, group: str) -> bool:
        presence = group in PRESENCE_GROUPS
        for phrase, pattern, compound in self.phrase_index.get(group, []):
            for m in pattern.finditer(text):
                if presence and self._negated(text, m.start(), m.end()):
                    continue
                return True
            if compound and phrase in text:
                # inside a German compound word, e.g. "vollmilchpulver"
                idx = text.find(phrase)
                while idx != -1:
                    if not (presence and self._negated(text, idx, idx + len(phrase))):
                        return True
                    idx = text.find(phrase, idx + 1)
        return False

    def match(self, ingredients: List[str], groups: List[str]) -> Dict[str, List[str]]:
        results: Dict[str, List[str]] = {}

        for group in groups:
            group_terms = self.ontology_index.get(group, set())
            presence = group in PRESENCE_GROUPS
            matched: List[str] = []

            for ingredient in ingredients:
                ingredient_norm = ingredient.strip().lower()
                if not ingredient_norm:
                    continue
                if group not in TRACE_RELEVANT_GROUPS and TRACE_PATTERN.search(ingredient_norm):
                    continue
                text = self._strip_exceptions(ingredient_norm, group) if presence else ingredient_norm
                text = re.sub(r"\s+", " ", text).strip()

                if ingredient_norm in group_terms and text == ingredient_norm:
                    matched.append(ingredient_norm)
                elif text and self._phrase_hit(text, group):
                    matched.append(ingredient_norm)

            results[group] = matched

        return results
