from backend.services.decision_engine import DecisionEngine


def test_all_positive_except_vegan():
    engine = DecisionEngine()
    matches = {
        "pork": [],
        "alcohol": [],
        "animal_products": ["milk powder"],
        "allergens": ["milk"],
        "regional_labels": ["aus der region"],
    }

    result = engine.evaluate(matches)

    assert result["halal"] is True
    assert result["vegan"] is False
    assert result["vegetarian"] is True
    assert result["allergen_warning"] is True
    assert result["regional"] is True


def test_pork_breaks_halal_and_vegetarian():
    engine = DecisionEngine()
    matches = {
        "pork": ["bacon"],
        "alcohol": [],
        "animal_products": [],
        "allergens": [],
        "regional_labels": [],
    }

    result = engine.evaluate(matches)

    assert result["halal"] is False
    assert result["vegetarian"] is False
    assert result["vegan"] is True
    assert result["allergen_warning"] is False
    assert result["regional"] is False


def test_alcohol_breaks_halal():
    engine = DecisionEngine()
    matches = {
        "pork": [],
        "alcohol": ["wine"],
        "animal_products": [],
        "allergens": [],
        "regional_labels": [],
    }

    result = engine.evaluate(matches)

    assert result["halal"] is False
    assert result["vegetarian"] is True
    assert result["vegan"] is True


def test_clean_product():
    engine = DecisionEngine()
    matches = {
        "pork": [],
        "alcohol": [],
        "animal_products": [],
        "allergens": [],
        "regional_labels": [],
    }

    result = engine.evaluate(matches)

    assert result["halal"] is True
    assert result["vegan"] is True
    assert result["vegetarian"] is True
    assert result["allergen_warning"] is False
    assert result["regional"] is False