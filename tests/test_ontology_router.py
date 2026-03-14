from backend.services.ontology_router import OntologyRouter

UNIVERSAL = [
    "allergens", "animal_products", "promotion_terms",
    "price_unit_aliases", "sugar_synonyms", "salt_synonyms",
]

def test_empty_returns_universal():
    assert OntologyRouter().route("") == UNIVERSAL

def test_whitespace_returns_universal():
    assert OntologyRouter().route("   ") == UNIVERSAL

def test_dairy_includes_lactose_and_vegan():
    result = OntologyRouter().route("dairy")
    assert all(g in result for g in UNIVERSAL)
    assert "lactose_free_labels" in result
    assert "vegan_markers" in result
    assert "vegetarian_markers" in result

def test_dairy_alternative_routed():
    result = OntologyRouter().route("dairy_alternative")
    assert "lactose_free_labels" in result
    assert "vegan_markers" in result

def test_meat_includes_pork():
    result = OntologyRouter().route("meat")
    assert "meat" in result
    assert "pork" in result

def test_fish_includes_histamine():
    result = OntologyRouter().route("fish")
    assert "fish_synonyms" in result
    assert "histamine_triggers" in result

def test_seafood_includes_shellfish():
    result = OntologyRouter().route("seafood")
    assert "shellfish_synonyms" in result

def test_snacks_includes_nuts():
    result = OntologyRouter().route("snacks")
    assert "nut_synonyms" in result

def test_sports_nutrition():
    result = OntologyRouter().route("sports nutrition")
    assert "sports_nutrition_markers" in result
    assert "high_protein_markers" in result

def test_unknown_returns_universal_only():
    assert OntologyRouter().route("cleaning products") == UNIVERSAL

def test_case_insensitive():
    r1 = OntologyRouter().route("dairy")
    r2 = OntologyRouter().route("DAIRY")
    r3 = OntologyRouter().route("Dairy")
    assert r1 == r2 == r3

def test_no_duplicates():
    result = OntologyRouter().route("dairy")
    assert len(result) == len(set(result))
