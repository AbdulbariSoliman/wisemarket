from typing import Dict, List


class DecisionEngine:
    """
    Convert ontology matches into product verdicts.

    Version 1 verdicts:
    - halal
    - vegan
    - vegetarian
    - allergen_warning
    - regional
    """

    def evaluate(self, matches: Dict[str, List[str]]) -> Dict[str, object]:
        pork_hits = matches.get("pork", [])
        alcohol_hits = matches.get("alcohol", [])
        animal_hits = matches.get("animal_products", [])
        allergen_hits = matches.get("allergens", [])
        regional_hits = matches.get("regional_labels", [])

        halal = len(pork_hits) == 0 and len(alcohol_hits) == 0
        vegan = len(animal_hits) == 0
        vegetarian = len(pork_hits) == 0
        allergen_warning = len(allergen_hits) > 0
        regional = len(regional_hits) > 0

        return {
            "halal": halal,
            "vegan": vegan,
            "vegetarian": vegetarian,
            "allergen_warning": allergen_warning,
            "regional": regional,
            "reasons": {
                "pork_hits": pork_hits,
                "alcohol_hits": alcohol_hits,
                "animal_hits": animal_hits,
                "allergen_hits": allergen_hits,
                "regional_hits": regional_hits,
            },
        }