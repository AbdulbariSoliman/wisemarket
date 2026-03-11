from backend.services.ontology_router import OntologyRouter


def test_empty_category_returns_universal_only():
    router = OntologyRouter()
    result = router.route("")
    assert result == [
        "allergens",
        "animal_products",
        "promotion_terms",
        "price_unit_aliases",
        "sugar_synonyms",
        "salt_synonyms",
    ]


def test_dairy_category():
    router = OntologyRouter()
    result = router.route("Dairy")
    assert result == [
        "allergens",
        "animal_products",
        "promotion_terms",
        "price_unit_aliases",
        "sugar_synonyms",
        "salt_synonyms",
        "lactose_free_labels",
        "vegan_markers",
        "vegetarian_markers",
    ]


def test_seafood_category():
    router = OntologyRouter()
    result = router.route("Seafood")
    assert result == [
        "allergens",
        "animal_products",
        "promotion_terms",
        "price_unit_aliases",
        "sugar_synonyms",
        "salt_synonyms",
        "fish_synonyms",
        "shellfish_synonyms",
        "histamine_triggers",
    ]


def test_unknown_category_returns_universal_only():
    router = OntologyRouter()
    result = router.route("Cleaning Products")
    assert result == [
        "allergens",
        "animal_products",
        "promotion_terms",
        "price_unit_aliases",
        "sugar_synonyms",
        "salt_synonyms",
    ]
