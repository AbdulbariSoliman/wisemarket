from typing import Dict, List, Set


class OntologyMatcher:
    """
    Match normalized ingredient tokens against selected ontology groups.

    Version 1:
    - receives ontology data already loaded in memory
    - checks only routed groups
    - returns matched ingredient tokens per group
    """

    def __init__(self, ontology_data: Dict[str, List[dict]]) -> None:
        self.ontology_index = self._build_index(ontology_data)

    def _build_index(self, ontology_data: Dict[str, List[dict]]) -> Dict[str, Set[str]]:
        index: Dict[str, Set[str]] = {}

        for group_name, rows in ontology_data.items():
            terms: Set[str] = set()

            for row in rows:
                for key in ("term", "en", "de", "fr", "it"):
                    value = row.get(key)
                    if not value:
                        continue

                    for part in str(value).split(";"):
                        token = part.strip().lower()
                        if token:
                            terms.add(token)

            index[group_name] = terms

        return index

    def match(self, ingredients: List[str], groups: List[str]) -> Dict[str, List[str]]:
        results: Dict[str, List[str]] = {}

        for group in groups:
            group_terms = self.ontology_index.get(group, set())
            matched: List[str] = []

            for ingredient in ingredients:
                ingredient_norm = ingredient.strip().lower()
                if ingredient_norm in group_terms:
                    matched.append(ingredient_norm)

            results[group] = matched

        return results