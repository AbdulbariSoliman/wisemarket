import pytest
from backend.services.decision_engine import DecisionEngine


def test_all_positive_except_vegan():
    # Milk product — has animal products so not vegan
    # no pork, no alcohol — halal and vegetarian
    engine = DecisionEngine()
    matches = {
        "pork": [],
        "alcohol": [],
        "animal_products": ["milk powder"],
        "allergens": ["milk"],
        "regional_labels": ["aus der region"],
        "vegan_markers": [],
        "vegetarian_markers": ["vegetarisch"],
    }
    result = engine.evaluate(matches)
    assert result["halal"] is True
    assert result["vegan"] is False
    assert result["vegan_likely"] is False
    assert result["vegetarian"] is True
    assert result["allergen_warning"] is True
    assert result["regional"] is True


def test_pork_breaks_halal_and_vegetarian():
    # Pork product — breaks halal and vegetarian
    # no animal_products hit + no vegan marker = vegan_likely only
    engine = DecisionEngine()
    matches = {
        "pork": ["bacon"],
        "alcohol": [],
        "animal_products": [],
        "allergens": [],
        "regional_labels": [],
        "vegan_markers": [],
        "vegetarian_markers": [],
    }
    result = engine.evaluate(matches)
    assert result["halal"] is False
    assert result["vegetarian"] is False
    assert result["vegan"] is False
    assert result["vegan_likely"] is True


def test_alcohol_breaks_halal():
    # Wine — breaks halal
    # no animal_products, no vegan marker = vegan_likely only
    engine = DecisionEngine()
    matches = {
        "pork": [],
        "alcohol": ["wine"],
        "animal_products": [],
        "allergens": [],
        "regional_labels": [],
        "vegan_markers": [],
        "vegetarian_markers": ["vegetarisch"],
    }
    result = engine.evaluate(matches)
    assert result["halal"] is False
    assert result["vegetarian"] is True
    assert result["vegan"] is False
    assert result["vegan_likely"] is True


def test_clean_product():
    # Completely clean product with vegan label
    engine = DecisionEngine()
    matches = {
        "pork": [],
        "alcohol": [],
        "animal_products": [],
        "allergens": [],
        "regional_labels": [],
        "vegan_markers": ["vegan"],
        "vegetarian_markers": ["vegetarisch"],
    }
    result = engine.evaluate(matches)
    assert result["halal"] is True
    assert result["vegan"] is True
    assert result["vegan_likely"] is True
    assert result["vegetarian"] is True
    assert result["allergen_warning"] is False


def test_gluten_free_verdict():
    # Product with gluten free label and no coeliac triggers
    engine = DecisionEngine()
    matches = {
        "pork": [], "alcohol": [], "animal_products": [],
        "allergens": [], "regional_labels": [],
        "vegan_markers": [], "vegetarian_markers": [],
        "gluten_free_labels": ["glutenfrei"],
        "coeliac_triggers": [],
    }
    result = engine.evaluate(matches)
    assert result["is_gluten_free"] is True


def test_lactose_free_verdict():
    engine = DecisionEngine()
    matches = {
        "pork": [], "alcohol": [], "animal_products": [],
        "allergens": [], "regional_labels": [],
        "vegan_markers": [], "vegetarian_markers": [],
        "lactose_free_labels": ["laktosefrei"],
    }
    result = engine.evaluate(matches)
    assert result["is_lactose_free"] is True


def test_bio_verdict():
    engine = DecisionEngine()
    matches = {
        "pork": [], "alcohol": [], "animal_products": [],
        "allergens": [], "regional_labels": [],
        "vegan_markers": [], "vegetarian_markers": [],
        "bio_labels": ["bio"],
        "organic_variants": [],
    }
    result = engine.evaluate(matches)
    assert result["is_bio"] is True


def test_keto_verdict():
    engine = DecisionEngine()
    matches = {
        "pork": [], "alcohol": [], "animal_products": [],
        "allergens": [], "regional_labels": [],
        "vegan_markers": [], "vegetarian_markers": [],
        "keto_markers": ["keto"],
        "low_sugar_markers": ["zuckerarm"],
    }
    result = engine.evaluate(matches)
    assert result["is_keto"] is True
    assert result["is_low_sugar"] is True
    assert result["is_diabetic_friendly"] is True


def test_high_protein_verdict():
    engine = DecisionEngine()
    matches = {
        "pork": [], "alcohol": [], "animal_products": [],
        "allergens": [], "regional_labels": [],
        "vegan_markers": [], "vegetarian_markers": [],
        "high_protein_markers": ["proteinreich"],
        "sports_nutrition_markers": [],
    }
    result = engine.evaluate(matches)
    assert result["is_high_protein"] is True


def test_kids_verdict():
    engine = DecisionEngine()
    matches = {
        "pork": [], "alcohol": [], "animal_products": [],
        "allergens": [], "regional_labels": [],
        "vegan_markers": [], "vegetarian_markers": [],
        "child_friendly_markers": ["kids"],
    }
    result = engine.evaluate(matches)
    assert result["is_kids_friendly"] is True


def test_packages_in_response():
    # Packages should be a list of dicts with id, label, icon, confidence
    engine = DecisionEngine()
    matches = {
        "pork": [], "alcohol": [], "animal_products": [],
        "allergens": ["milk"], "regional_labels": ["schweizer"],
        "vegan_markers": ["vegan"], "vegetarian_markers": ["vegetarisch"],
        "bio_labels": ["bio"], "keto_markers": [],
        "low_sugar_markers": [], "high_protein_markers": [],
        "child_friendly_markers": [], "sports_nutrition_markers": [],
        "caffeine": [], "palm_oil": [], "histamine_triggers": [],
        "sulphite_markers": [], "vitamin_markers": [],
        "mineral_markers": [], "superfood_markers": [],
        "probiotic_prebiotic": [], "eco_packaging": [],
        "animal_welfare": [], "fairtrade_labels": [],
        "sustainability_labels": [], "gluten_free_labels": [],
        "coeliac_triggers": [], "lactose_free_labels": [],
        "organic_variants": [], "fiber_markers": [],
        "low_fat_markers": [], "antioxidant_markers": [],
        "diabetic_markers": [],
    }
    result = engine.evaluate(matches, lang="de")
    assert isinstance(result["packages"], list)
    assert len(result["packages"]) > 0
    for pkg in result["packages"]:
        assert "id" in pkg
        assert "label" in pkg
        assert "icon" in pkg
        assert "confidence" in pkg


def test_packages_multilingual():
    # Same product different lang should give different labels
    engine = DecisionEngine()
    matches = {
        "pork": [], "alcohol": [], "animal_products": [],
        "allergens": [], "regional_labels": [],
        "vegan_markers": ["vegan"], "vegetarian_markers": [],
        "bio_labels": ["bio"], "keto_markers": [],
        "low_sugar_markers": [], "high_protein_markers": [],
        "child_friendly_markers": [], "sports_nutrition_markers": [],
        "caffeine": [], "palm_oil": [], "histamine_triggers": [],
        "sulphite_markers": [], "vitamin_markers": [],
        "mineral_markers": [], "superfood_markers": [],
        "probiotic_prebiotic": [], "eco_packaging": [],
        "animal_welfare": [], "fairtrade_labels": [],
        "sustainability_labels": [], "gluten_free_labels": [],
        "coeliac_triggers": [], "lactose_free_labels": [],
        "organic_variants": [], "fiber_markers": [],
        "low_fat_markers": [], "antioxidant_markers": [],
        "diabetic_markers": [],
    }
    result_en = engine.evaluate(matches, lang="en")
    result_de = engine.evaluate(matches, lang="de")
    result_fr = engine.evaluate(matches, lang="fr")

    en_labels = {p["id"]: p["label"] for p in result_en["packages"]}
    de_labels = {p["id"]: p["label"] for p in result_de["packages"]}
    fr_labels = {p["id"]: p["label"] for p in result_fr["packages"]}

    assert en_labels["vegan"] == "Vegan"
    assert de_labels["vegan"] == "Vegan"
    assert fr_labels["vegan"] == "Végane"
    assert en_labels["bio"] == "Organic / Bio"
    assert de_labels["bio"] == "Bio / Biologisch"
    assert fr_labels["bio"] == "Bio / Biologique"
