from typing import List


class OntologyRouter:
    """
    Route a product category to relevant ontology groups.

    Version 1:
    - always include universal groups
    - add category-specific groups
    - simple keyword-based routing
    """

    def __init__(self) -> None:
        self.universal_groups = [
            "allergens",
            "animal_products",
            "promotion_terms",
            "price_unit_aliases",
            "sugar_synonyms",
            "salt_synonyms",
            # Safety groups: checked for every product, because they decide
            # halal / vegan / vegetarian / gluten / palm-oil verdicts and the
            # ingredient (e.g. gelatine, lard, wine, palm oil) can appear in
            # any category, not only meat or snacks.
            "pork",
            "alcohol",
            "meat",
            "fish_synonyms",
            "shellfish_synonyms",
            "palm_oil",
            "coeliac_triggers",
            "gluten_free_labels",
            "lactose_free_labels",
            "vegan_markers",
            "vegetarian_markers",
            "egg_synonyms",
            "halal_labels",
        ]

        self.category_routes = {
            "dairy": [
                "lactose_free_labels",
                "vegan_markers",
                "vegetarian_markers",
                "bio_labels",
                "organic_variants",
                "animal_welfare",
            ],
            "dairy_alternative": [
                "lactose_free_labels",
                "vegan_markers",
                "vegetarian_markers",
            ],
            "seafood": [
                "fish_synonyms",
                "shellfish_synonyms",
                "histamine_triggers",
                "sulphite_markers",
            ],
            "fish": [
                "fish_synonyms",
                "shellfish_synonyms",
                "histamine_triggers",
                "sulphite_markers",
            ],
            "meat": [
                "meat",
                "pork",
                "animal_welfare",
                "bio_labels",
                "organic_variants",
            ],
            "poultry": [
                "meat",
                "pork",
                "animal_welfare",
            ],
            "snacks": [
                "nut_synonyms",
                "superfood_markers",
                "palm_oil",
                "caffeine",
                "sugar_synonyms",
                "artificial_sweeteners",
            ],
            "chocolate": [
                "vegan_markers",
                "palm_oil",
                "fairtrade_labels",
                "superfood_markers",
                "sugar_synonyms",
            ],
            "bakery": [
                "vegan_markers",
                "vegetarian_markers",
                "gluten_free_labels",
                "coeliac_triggers",
                "egg_synonyms",
                "alcohol",
            ],
            "bread": [
                "vegan_markers",
                "gluten_free_labels",
                "coeliac_triggers",
            ],
            "beverages": [
                "caffeine",
                "sugar_synonyms",
                "artificial_sweeteners",
                "alcohol",
                "vegan_markers",
            ],
            "pantry": [
                "vegan_markers",
                "vegetarian_markers",
                "gluten_free_labels",
                "coeliac_triggers",
                "bio_labels",
                "organic_variants",
                "fairtrade_labels",
            ],
            "frozen": [
                "vegan_markers",
                "vegetarian_markers",
                "gluten_free_labels",
            ],
            "fresh_produce": [
                "vegan_markers",
                "bio_labels",
                "organic_variants",
                "regional_labels",
                "fairtrade_labels",
                "sustainability_labels",
            ],
            "plant_protein": [
                "vegan_markers",
                "high_protein_markers",
                "protein_vegan",
                "soy_synonyms",
            ],
            "sports nutrition": [
                "sports_nutrition_markers",
                "high_protein_markers",
                "protein_animal",
                "protein_vegan",
                "keto_markers",
            ],
            "baby": [
                "child_friendly_markers",
                "allergens",
                "lactose_free_labels",
                "vitamin_markers",
                "mineral_markers",
            ],
        }

    def route(self, category: str) -> List[str]:
        if not category or not category.strip():
            return self.universal_groups.copy()

        category_norm = category.strip().lower()

        matched_groups = self.universal_groups.copy()

        for key, groups in self.category_routes.items():
            if key in category_norm:
                for group in groups:
                    if group not in matched_groups:
                        matched_groups.append(group)

        return matched_groups