from typing import Any, Dict, List


# ─── PACKAGE LABELS IN 4 LANGUAGES ──────────────────────────────────────────
PACKAGE_LABELS = {
    "halal": {
        "en": "Halal", "de": "Halal", "fr": "Halal", "it": "Halal",
        "icon": "☪️",
    },
    "vegan": {
        "en": "Vegan", "de": "Vegan", "fr": "Végane", "it": "Vegano",
        "icon": "🌱",
    },
    "vegan_likely": {
        "en": "Likely Vegan", "de": "Wahrscheinlich Vegan", "fr": "Probablement Végane", "it": "Probabilmente Vegano",
        "icon": "🌿",
    },
    "vegetarian": {
        "en": "Vegetarian", "de": "Vegetarisch", "fr": "Végétarien", "it": "Vegetariano",
        "icon": "🥦",
    },
    "gluten_free": {
        "en": "Gluten Free", "de": "Glutenfrei", "fr": "Sans Gluten", "it": "Senza Glutine",
        "icon": "🌾",
    },
    "lactose_free": {
        "en": "Lactose Free", "de": "Laktosefrei", "fr": "Sans Lactose", "it": "Senza Lattosio",
        "icon": "🥛",
    },
    "keto": {
        "en": "Keto Friendly", "de": "Keto-Freundlich", "fr": "Keto Friendly", "it": "Keto Friendly",
        "icon": "🥑",
    },
    "low_sugar": {
        "en": "Low Sugar", "de": "Zuckerarm", "fr": "Pauvre en Sucre", "it": "Povero di Zucchero",
        "icon": "🍬",
    },
    "low_fat": {
        "en": "Low Fat", "de": "Fettarm", "fr": "Pauvre en Graisses", "it": "Povero di Grassi",
        "icon": "💧",
    },
    "diabetic_friendly": {
        "en": "Diabetic Friendly", "de": "Diabetikerfreundlich", "fr": "Adapté aux Diabétiques", "it": "Adatto ai Diabetici",
        "icon": "🩺",
    },
    "high_protein": {
        "en": "High Protein", "de": "Proteinreich", "fr": "Riche en Protéines", "it": "Ricco di Proteine",
        "icon": "💪",
    },
    "high_fiber": {
        "en": "High Fiber", "de": "Ballaststoffreich", "fr": "Riche en Fibres", "it": "Ricco di Fibre",
        "icon": "🌾",
    },
    "vitamins": {
        "en": "Rich in Vitamins", "de": "Vitaminreich", "fr": "Riche en Vitamines", "it": "Ricco di Vitamine",
        "icon": "💊",
    },
    "minerals": {
        "en": "Rich in Minerals", "de": "Mineralstoffreich", "fr": "Riche en Minéraux", "it": "Ricco di Minerali",
        "icon": "⚡",
    },
    "antioxidants": {
        "en": "Antioxidant Rich", "de": "Antioxidantienreich", "fr": "Riche en Antioxydants", "it": "Ricco di Antiossidanti",
        "icon": "🫐",
    },
    "superfoods": {
        "en": "Contains Superfoods", "de": "Enthält Superfoods", "fr": "Contient des Superaliments", "it": "Contiene Supercibi",
        "icon": "✨",
    },
    "probiotics": {
        "en": "Probiotic", "de": "Probiotisch", "fr": "Probiotique", "it": "Probiotico",
        "icon": "🦠",
    },
    "bio": {
        "en": "Organic / Bio", "de": "Bio / Biologisch", "fr": "Bio / Biologique", "it": "Bio / Biologico",
        "icon": "🌿",
    },
    "fairtrade": {
        "en": "Fairtrade", "de": "Fairtrade", "fr": "Commerce Équitable", "it": "Commercio Equo",
        "icon": "⚖️",
    },
    "sustainable": {
        "en": "Sustainable", "de": "Nachhaltig", "fr": "Durable", "it": "Sostenibile",
        "icon": "♻️",
    },
    "animal_welfare": {
        "en": "Animal Welfare", "de": "Tierwohl", "fr": "Bien-être Animal", "it": "Benessere Animale",
        "icon": "🐄",
    },
    "regional": {
        "en": "Swiss / Regional", "de": "Schweizer / Regional", "fr": "Suisse / Régional", "it": "Svizzero / Regionale",
        "icon": "🇨🇭",
    },
    "sports": {
        "en": "Sports Nutrition", "de": "Sporternährung", "fr": "Nutrition Sportive", "it": "Nutrizione Sportiva",
        "icon": "🏋️",
    },
    "kids": {
        "en": "Kids Friendly", "de": "Kinderfreundlich", "fr": "Adapté aux Enfants", "it": "Adatto ai Bambini",
        "icon": "👶",
    },
    "allergen_warning": {
        "en": "Contains Allergens", "de": "Enthält Allergene", "fr": "Contient des Allergènes", "it": "Contiene Allergeni",
        "icon": "⚠️",
    },
    "caffeine": {
        "en": "Contains Caffeine", "de": "Enthält Koffein", "fr": "Contient de la Caféine", "it": "Contiene Caffeina",
        "icon": "☕",
    },
    "palm_oil": {
        "en": "Contains Palm Oil", "de": "Enthält Palmöl", "fr": "Contient de l'Huile de Palme", "it": "Contiene Olio di Palma",
        "icon": "🌴",
    },
    "histamine_risk": {
        "en": "Histamine Risk", "de": "Histaminrisiko", "fr": "Risque Histamine", "it": "Rischio Istamina",
        "icon": "🔴",
    },
    "sulphites": {
        "en": "Contains Sulphites", "de": "Enthält Sulfite", "fr": "Contient des Sulfites", "it": "Contiene Solfiti",
        "icon": "⚗️",
    },
}


def _build_packages(verdicts: Dict[str, Any], lang: str = "en") -> List[Dict[str, str]]:
    """
    Groups verdicts into user-facing product packages/labels.
    Returns labels in the requested language (en/de/fr/it).

    Each package:
      - id: machine key
      - label: translated user-facing name
      - icon: emoji
      - confidence: high / medium
    """
    if lang not in ("en", "de", "fr", "it"):
        lang = "en"

    packages = []

    def add(id: str, confidence: str = "high"):
        info = PACKAGE_LABELS.get(id)
        if not info:
            return
        packages.append({
            "id": id,
            "label": info.get(lang, info.get("en", id)),
            "icon": info.get("icon", ""),
            "confidence": confidence,
        })

    # ─── DIETARY ──────────────────────────────────────────────────
    if verdicts["halal"]:
        add("halal")
    if verdicts["vegan"]:
        add("vegan")
    elif verdicts["vegan_likely"]:
        add("vegan_likely", "medium")
    if verdicts["vegetarian"]:
        add("vegetarian")
    if verdicts["is_gluten_free"]:
        add("gluten_free")
    if verdicts["is_lactose_free"]:
        add("lactose_free")
    if verdicts["is_keto"]:
        add("keto")
    if verdicts["is_low_sugar"]:
        add("low_sugar")
    if verdicts["is_low_fat"]:
        add("low_fat")
    if verdicts["is_diabetic_friendly"]:
        add("diabetic_friendly", "medium")

    # ─── NUTRITION ────────────────────────────────────────────────
    if verdicts["is_high_protein"]:
        add("high_protein")
    if verdicts["is_high_fiber"]:
        add("high_fiber")
    if verdicts["has_vitamins"]:
        add("vitamins")
    if verdicts["has_minerals"]:
        add("minerals")
    if verdicts["has_antioxidants"]:
        add("antioxidants")
    if verdicts["has_superfoods"]:
        add("superfoods")
    if verdicts["has_probiotics"]:
        add("probiotics")

    # ─── LABELS ───────────────────────────────────────────────────
    if verdicts["is_bio"]:
        add("bio")
    if verdicts["is_fairtrade"]:
        add("fairtrade")
    if verdicts["is_sustainable"]:
        add("sustainable")
    if verdicts["is_animal_welfare"]:
        add("animal_welfare")
    if verdicts["regional"]:
        add("regional")

    # ─── LIFESTYLE ────────────────────────────────────────────────
    if verdicts["is_sports"]:
        add("sports")
    if verdicts["is_kids_friendly"]:
        add("kids")

    # ─── WARNINGS ─────────────────────────────────────────────────
    if verdicts["allergen_warning"]:
        add("allergen_warning")
    if verdicts["has_caffeine"]:
        add("caffeine")
    if verdicts["has_palm_oil"]:
        add("palm_oil")
    if verdicts["has_histamine_risk"]:
        add("histamine_risk", "medium")
    if verdicts["has_sulphites"]:
        add("sulphites")

    return packages


_NON_VEGETARIAN_ANIMAL_WORDS = (
    "gelatin", "gélatine", "gelatina", "collagen", "kollagen", "collagène", "collagene",
    "lard", "schmalz", "saindoux", "strutto", "tallow", "talg", "suif", "sego",
    "fleisch", "viande", "meat", "carne", "fish", "fisch", "poisson", "pesce",
)


# Animal ingredients that need halal slaughter/certification (fish does not).
_HALAL_SENSITIVE_WORDS = (
    "gelatin", "gélatine", "gelatina", "collagen", "kollagen", "collagène", "collagene",
    "lard", "schmalz", "saindoux", "strutto", "tallow", "talg", "suif", "sego",
    "fleisch", "viande", "meat", "carne",
)


def _has_slaughter_product(animal_hits: List[str]) -> bool:
    """True if any animal hit is a slaughter product (gelatine, lard, meat, fish)."""
    return any(w in hit for hit in animal_hits for w in _NON_VEGETARIAN_ANIMAL_WORDS)


class DecisionEngine:
    """
    Convert ontology matches into product verdicts and packages.

    Version 2 verdicts:
      Core:       halal, vegan, vegetarian
      Dietary:    gluten_free, lactose_free, keto, low_sugar,
                  low_fat, high_protein, high_fiber, diabetic_friendly
      Labels:     bio, fairtrade, sustainable, regional, kids, sports
      Nutrition:  vitamins, minerals, antioxidants, superfoods, probiotics
      Warnings:   allergen_warning, caffeine, palm_oil,
                  histamine_risk, sulphites
      Packages:   grouped multilingual user-facing labels
    """

    def evaluate(
        self,
        matches: Dict[str, List[str]],
        lang: str = "en",
    ) -> Dict[str, Any]:

        # ─── RAW HITS ────────────────────────────────────────────────
        pork_hits           = matches.get("pork", [])
        alcohol_hits        = matches.get("alcohol", [])
        animal_hits         = matches.get("animal_products", [])
        allergen_hits       = matches.get("allergens", [])
        regional_hits       = matches.get("regional_labels", [])
        gluten_free_hits    = matches.get("gluten_free_labels", [])
        coeliac_hits        = matches.get("coeliac_triggers", [])
        lactose_free_hits   = matches.get("lactose_free_labels", [])
        bio_hits            = matches.get("bio_labels", [])
        organic_hits        = matches.get("organic_variants", [])
        fairtrade_hits      = matches.get("fairtrade_labels", [])
        sustain_hits        = matches.get("sustainability_labels", [])
        keto_hits           = matches.get("keto_markers", [])
        low_sugar_hits      = matches.get("low_sugar_markers", [])
        low_fat_hits        = matches.get("low_fat_markers", [])
        high_protein_hits   = matches.get("high_protein_markers", [])
        fiber_hits          = matches.get("fiber_markers", [])
        kids_hits           = matches.get("child_friendly_markers", [])
        sports_hits         = matches.get("sports_nutrition_markers", [])
        caffeine_hits       = matches.get("caffeine", [])
        palm_oil_hits       = matches.get("palm_oil", [])
        histamine_hits      = matches.get("histamine_triggers", [])
        sulphite_hits       = matches.get("sulphite_markers", [])
        diabetic_hits       = matches.get("diabetic_markers", [])
        vegan_marker_hits   = matches.get("vegan_markers", [])
        vegetarian_hits     = matches.get("vegetarian_markers", [])
        vitamin_hits        = matches.get("vitamin_markers", [])
        mineral_hits        = matches.get("mineral_markers", [])
        antioxidant_hits    = matches.get("antioxidant_markers", [])
        superfood_hits      = matches.get("superfood_markers", [])
        probiotic_hits      = matches.get("probiotic_prebiotic", [])
        eco_hits            = matches.get("eco_packaging", [])
        animal_welfare_hits = matches.get("animal_welfare", [])
        meat_hits           = matches.get("meat", [])
        fish_hits           = matches.get("fish_synonyms", [])
        shellfish_hits      = matches.get("shellfish_synonyms", [])
        # Animal-derived but compatible with a vegetarian diet (milk, eggs, honey)
        # vs. ingredients that require killing an animal (meat, fish, gelatine, lard)
        non_vegetarian_hits = pork_hits + meat_hits + fish_hits + shellfish_hits

        # ─── CORE VERDICTS ───────────────────────────────────────────
        halal_label_hits   = matches.get("halal_labels", [])
        slaughter_product  = _has_slaughter_product(animal_hits)
        # Any animal ingredient at all (dairy, egg, honey, meat, fish, ...)
        egg_hits           = matches.get("egg_synonyms", [])
        any_animal         = bool(animal_hits) or bool(non_vegetarian_hits) or bool(egg_hits)
        # Meat, gelatine or lard is only halal when the product says so;
        # fish and seafood are halal without a label.
        needs_halal_label  = bool(meat_hits) or any(
            w in h for h in animal_hits for w in _HALAL_SENSITIVE_WORDS)
        halal              = (not pork_hits and not alcohol_hits
                              and (not needs_halal_label or bool(halal_label_hits)))
        vegan              = not any_animal and bool(vegan_marker_hits)
        vegan_likely       = not any_animal
        vegetarian         = not non_vegetarian_hits and not slaughter_product
        allergen_warning   = bool(allergen_hits)
        regional           = bool(regional_hits)

        # ─── DIETARY VERDICTS ────────────────────────────────────────
        is_gluten_free     = bool(gluten_free_hits) and not bool(coeliac_hits)
        is_lactose_free    = bool(lactose_free_hits)
        is_keto            = bool(keto_hits)
        is_low_sugar       = bool(low_sugar_hits)
        is_low_fat         = bool(low_fat_hits)
        is_high_protein    = bool(high_protein_hits) or bool(sports_hits)
        is_high_fiber      = bool(fiber_hits)
        is_diabetic_friendly = bool(diabetic_hits) or bool(low_sugar_hits)

        # ─── LABEL VERDICTS ──────────────────────────────────────────
        is_bio             = bool(bio_hits) or bool(organic_hits)
        is_fairtrade       = bool(fairtrade_hits)
        is_sustainable     = bool(sustain_hits) or bool(eco_hits)
        is_kids_friendly   = bool(kids_hits)
        is_sports          = bool(sports_hits)
        is_animal_welfare  = bool(animal_welfare_hits)

        # ─── WARNING VERDICTS ────────────────────────────────────────
        has_caffeine       = bool(caffeine_hits)
        has_palm_oil       = bool(palm_oil_hits)
        has_histamine_risk = bool(histamine_hits)
        has_sulphites      = bool(sulphite_hits)

        # ─── NUTRITION VERDICTS ──────────────────────────────────────
        has_vitamins       = bool(vitamin_hits)
        has_minerals       = bool(mineral_hits)
        has_antioxidants   = bool(antioxidant_hits)
        has_superfoods     = bool(superfood_hits)
        has_probiotics     = bool(probiotic_hits)

        # ─── ASSEMBLE VERDICTS ───────────────────────────────────────
        verdicts = {
            "halal":               halal,
            "vegan":               vegan,
            "vegan_likely":        vegan_likely,
            "vegetarian":          vegetarian,
            "allergen_warning":    allergen_warning,
            "regional":            regional,
            "is_gluten_free":      is_gluten_free,
            "is_lactose_free":     is_lactose_free,
            "is_keto":             is_keto,
            "is_low_sugar":        is_low_sugar,
            "is_low_fat":          is_low_fat,
            "is_high_protein":     is_high_protein,
            "is_high_fiber":       is_high_fiber,
            "is_diabetic_friendly":is_diabetic_friendly,
            "is_bio":              is_bio,
            "is_fairtrade":        is_fairtrade,
            "is_sustainable":      is_sustainable,
            "is_kids_friendly":    is_kids_friendly,
            "is_sports":           is_sports,
            "is_animal_welfare":   is_animal_welfare,
            "has_caffeine":        has_caffeine,
            "has_palm_oil":        has_palm_oil,
            "has_histamine_risk":  has_histamine_risk,
            "has_sulphites":       has_sulphites,
            "has_vitamins":        has_vitamins,
            "has_minerals":        has_minerals,
            "has_antioxidants":    has_antioxidants,
            "has_superfoods":      has_superfoods,
            "has_probiotics":      has_probiotics,
            "reasons": {
                "pork_hits":        pork_hits,
                "alcohol_hits":     alcohol_hits,
                "animal_hits":      animal_hits,
                "non_vegetarian_hits": non_vegetarian_hits,
                "allergen_hits":    allergen_hits,
                "regional_hits":    regional_hits,
                "gluten_free_hits": gluten_free_hits,
                "lactose_free_hits":lactose_free_hits,
                "bio_hits":         bio_hits,
                "keto_hits":        keto_hits,
                "low_sugar_hits":   low_sugar_hits,
                "high_protein_hits":high_protein_hits,
                "kids_hits":        kids_hits,
                "sports_hits":      sports_hits,
                "caffeine_hits":    caffeine_hits,
                "palm_oil_hits":    palm_oil_hits,
                "histamine_hits":   histamine_hits,
                "sulphite_hits":    sulphite_hits,
                "vitamin_hits":     vitamin_hits,
                "mineral_hits":     mineral_hits,
                "superfood_hits":   superfood_hits,
                "probiotic_hits":   probiotic_hits,
            },
        }

        # ─── PACKAGES IN REQUESTED LANGUAGE ─────────────────────────
        verdicts["packages"] = _build_packages(verdicts, lang=lang)

        return verdicts
