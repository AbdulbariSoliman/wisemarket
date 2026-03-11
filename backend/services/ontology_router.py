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
        ]

        self.category_routes = {
            "dairy": [
                "lactose_free_labels",
                "vegan_markers",
                "vegetarian_markers",
            ],
            "seafood": [
                "fish_synonyms",
                "shellfish_synonyms",
                "histamine_triggers",
            ],
            "meat": [
                "meat",
                "pork",
            ],
            "snacks": [
                "nut_synonyms",
                "superfood_markers",
            ],
            "sports nutrition": [
                "sports_nutrition_markers",
                "high_protein_markers",
                "protein_animal",
                "protein_vegan",
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