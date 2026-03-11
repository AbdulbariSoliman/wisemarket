from backend.services.ontology_matcher import OntologyMatcher


def build_matcher():
    ontology_data = {
        "allergens": [
            {
                "term": "milk",
                "en": "milk; lactose",
                "de": "milch",
                "fr": "lait",
                "it": "latte",
            }
        ],
        "animal_products": [
            {
                "term": "milk powder",
                "en": "milk powder",
                "de": "milchpulver",
                "fr": "poudre de lait",
                "it": "latte in polvere",
            }
        ],
        "fish_synonyms": [
            {
                "term": "tuna",
                "en": "tuna",
                "de": "thunfisch",
                "fr": "thon",
                "it": "tonno",
            }
        ],
    }
    return OntologyMatcher(ontology_data)


def test_match_single_group():
    matcher = build_matcher()
    result = matcher.match(["milk", "sugar"], ["allergens"])
    assert result == {"allergens": ["milk"]}


def test_match_multiple_groups():
    matcher = build_matcher()
    result = matcher.match(
        ["milk", "milk powder", "salt"],
        ["allergens", "animal_products"],
    )
    assert result == {
        "allergens": ["milk"],
        "animal_products": ["milk powder"],
    }


def test_no_matches():
    matcher = build_matcher()
    result = matcher.match(["sugar", "salt"], ["allergens", "animal_products"])
    assert result == {
        "allergens": [],
        "animal_products": [],
    }


def test_unknown_group():
    matcher = build_matcher()
    result = matcher.match(["milk"], ["unknown_group"])
    assert result == {"unknown_group": []}


def test_fish_group():
    matcher = build_matcher()
    result = matcher.match(["tuna", "salt"], ["fish_synonyms"])
    assert result == {"fish_synonyms": ["tuna"]}