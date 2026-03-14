import pytest
from backend.services.decision_engine import DecisionEngine

def empty_matches(**overrides):
    base = {
        "pork": [], "alcohol": [], "animal_products": [],
        "allergens": [], "regional_labels": [],
        "vegan_markers": [], "vegetarian_markers": [],
        "gluten_free_labels": [], "coeliac_triggers": [],
        "lactose_free_labels": [], "bio_labels": [],
        "organic_variants": [], "fairtrade_labels": [],
        "sustainability_labels": [], "keto_markers": [],
        "low_sugar_markers": [], "low_fat_markers": [],
        "high_protein_markers": [], "fiber_markers": [],
        "child_friendly_markers": [], "sports_nutrition_markers": [],
        "caffeine": [], "palm_oil": [], "histamine_triggers": [],
        "sulphite_markers": [], "diabetic_markers": [],
        "vitamin_markers": [], "mineral_markers": [],
        "antioxidant_markers": [], "superfood_markers": [],
        "probiotic_prebiotic": [], "eco_packaging": [],
        "animal_welfare": [], "meat": [],
        "fish_synonyms": [], "shellfish_synonyms": [],
        "nut_synonyms": [], "soy_synonyms": [], "egg_synonyms": [],
    }
    base.update(overrides)
    return base

engine = DecisionEngine()

class TestAlcohol:
    def test_wine_not_halal(self):
        result = engine.evaluate(empty_matches(alcohol=["wine"]))
        assert result["halal"] is False

    def test_beer_not_halal(self):
        result = engine.evaluate(empty_matches(alcohol=["beer"]))
        assert result["halal"] is False

    def test_rum_cake_not_halal_not_vegan(self):
        result = engine.evaluate(empty_matches(
            alcohol=["rum"], animal_products=["eggs", "butter"]
        ))
        assert result["halal"] is False
        assert result["vegan"] is False
        assert result["vegan_likely"] is False

    def test_tiramisu_not_halal_not_vegan_has_caffeine(self):
        result = engine.evaluate(empty_matches(
            alcohol=["marsala wine"],
            animal_products=["eggs", "mascarpone"],
            caffeine=["coffee"],
        ))
        assert result["halal"] is False
        assert result["vegan"] is False
        assert result["has_caffeine"] is True

    def test_vanilla_extract_alcohol_not_halal(self):
        result = engine.evaluate(empty_matches(alcohol=["ethanol"]))
        assert result["halal"] is False

class TestPorkAndGelatin:
    def test_pork_sausage_not_halal_not_vegetarian(self):
        result = engine.evaluate(empty_matches(
            pork=["pork", "pork fat"], animal_products=["pork"]
        ))
        assert result["halal"] is False
        assert result["vegetarian"] is False
        assert result["vegan"] is False

    def test_pork_gelatin_sweets_not_halal(self):
        result = engine.evaluate(empty_matches(
            pork=["pork gelatin"], animal_products=["gelatin"]
        ))
        assert result["halal"] is False
        assert result["vegetarian"] is False
        assert result["vegan"] is False

    def test_marshmallows_pork_gelatin(self):
        result = engine.evaluate(empty_matches(
            pork=["gelatin"], animal_products=["gelatin"]
        ))
        assert result["halal"] is False
        assert result["vegetarian"] is False

    def test_beef_gelatin_halal_passes(self):
        """Beef gelatin — no pork, no alcohol — halal is True"""
        result = engine.evaluate(empty_matches(animal_products=["beef gelatin"]))
        assert result["halal"] is True
        assert result["vegan"] is False
        assert result["vegetarian"] is False

    def test_lard_in_pastry(self):
        result = engine.evaluate(empty_matches(
            pork=["lard"], animal_products=["lard"]
        ))
        assert result["halal"] is False
        assert result["vegan"] is False
        assert result["vegetarian"] is False

class TestVeganEdgeCases:
    def test_honey_not_vegan(self):
        result = engine.evaluate(empty_matches(animal_products=["honey"]))
        assert result["vegan"] is False
        assert result["vegan_likely"] is False

    def test_carmine_not_vegan(self):
        result = engine.evaluate(empty_matches(
            animal_products=["carmine", "e120"]
        ))
        assert result["vegan"] is False

    def test_whey_not_vegan(self):
        result = engine.evaluate(empty_matches(
            animal_products=["whey"], allergens=["milk"]
        ))
        assert result["vegan"] is False
        assert result["allergen_warning"] is True

    def test_dark_chocolate_vegan(self):
        result = engine.evaluate(empty_matches(vegan_markers=["vegan"]))
        assert result["vegan"] is True
        assert result["halal"] is True

    def test_plain_rice_vegan_likely_only(self):
        """No animal products, no vegan label → vegan_likely not vegan"""
        result = engine.evaluate(empty_matches())
        assert result["vegan"] is False
        assert result["vegan_likely"] is True

    def test_egg_breaks_vegan(self):
        result = engine.evaluate(empty_matches(
            animal_products=["eggs"], allergens=["eggs"]
        ))
        assert result["vegan"] is False
        assert result["vegan_likely"] is False

    def test_casein_not_vegan(self):
        result = engine.evaluate(empty_matches(
            animal_products=["casein"], allergens=["milk"]
        ))
        assert result["vegan"] is False

class TestBakedGoods:
    def test_croissant_not_vegan_halal_ok(self):
        result = engine.evaluate(empty_matches(
            animal_products=["butter", "milk", "eggs"],
            allergens=["milk", "eggs", "gluten"],
        ))
        assert result["vegan"] is False
        assert result["vegan_likely"] is False
        assert result["halal"] is True
        assert result["allergen_warning"] is True

    def test_rum_baba_not_halal(self):
        result = engine.evaluate(empty_matches(
            alcohol=["rum"],
            animal_products=["eggs", "butter"],
            allergens=["gluten", "eggs", "milk"],
        ))
        assert result["halal"] is False
        assert result["vegan"] is False

    def test_gluten_free_claim_blocked_by_coeliac_trigger(self):
        """GF label present but coeliac trigger also present — not GF"""
        result = engine.evaluate(empty_matches(
            gluten_free_labels=["glutenfrei"],
            coeliac_triggers=["wheat starch"],
        ))
        assert result["is_gluten_free"] is False

    def test_cheese_fondue_alcohol_no_halal(self):
        """Fondue: alcohol (not halal), dairy (not vegan), regional.
        Vegetarian requires either vegetarian_markers OR no animal_hits.
        Fondue has animal_products so needs explicit vegetarian marker."""
        result = engine.evaluate(empty_matches(
            alcohol=["white wine", "kirsch"],
            animal_products=["gruyere", "milk"],
            allergens=["milk"],
            regional_labels=["schweizer"],
            vegetarian_markers=["vegetarisch"],  # cheese IS vegetarian
        ))
        assert result["halal"] is False
        assert result["vegetarian"] is True
        assert result["regional"] is True

class TestAllergens:
    def test_multiple_allergens(self):
        result = engine.evaluate(empty_matches(
            allergens=["gluten", "milk", "eggs", "soy", "nuts"]
        ))
        assert result["allergen_warning"] is True

    def test_sulphites_in_wine(self):
        result = engine.evaluate(empty_matches(
            alcohol=["wine"], sulphite_markers=["sulphites"]
        ))
        assert result["halal"] is False
        assert result["has_sulphites"] is True

    def test_histamine_aged_cheese(self):
        result = engine.evaluate(empty_matches(
            animal_products=["milk"],
            histamine_triggers=["aged cheese"],
            allergens=["milk"],
        ))
        assert result["has_histamine_risk"] is True
        assert result["allergen_warning"] is True

class TestNutritionLabels:
    def test_diabetic_friendly(self):
        result = engine.evaluate(empty_matches(
            low_sugar_markers=["zuckerfrei"],
            diabetic_markers=["diabetiker geeignet"],
        ))
        assert result["is_low_sugar"] is True
        assert result["is_diabetic_friendly"] is True

    def test_keto_product(self):
        result = engine.evaluate(empty_matches(
            keto_markers=["keto"],
            high_protein_markers=["proteinreich"],
            low_sugar_markers=["zuckerarm"],
        ))
        assert result["is_keto"] is True
        assert result["is_high_protein"] is True
        assert result["is_diabetic_friendly"] is True

    def test_vegan_protein_powder(self):
        result = engine.evaluate(empty_matches(
            vegan_markers=["vegan"],
            high_protein_markers=["proteinreich"],
            sports_nutrition_markers=["sports"],
        ))
        assert result["vegan"] is True
        assert result["is_high_protein"] is True
        assert result["is_sports"] is True
        assert result["halal"] is True

    def test_energy_drink_caffeine_not_kids(self):
        result = engine.evaluate(empty_matches(caffeine=["caffeine"]))
        assert result["has_caffeine"] is True
        assert result["is_kids_friendly"] is False

    def test_salmon_halal_histamine_high_protein(self):
        result = engine.evaluate(empty_matches(
            animal_products=["salmon"],
            allergens=["fish"],
            high_protein_markers=["proteinreich"],
            histamine_triggers=["smoked fish"],
            sulphite_markers=["sulphites"],
        ))
        assert result["halal"] is True
        assert result["is_high_protein"] is True
        assert result["has_histamine_risk"] is True
        assert result["has_sulphites"] is True

class TestPackages:
    def test_halal_package_present(self):
        result = engine.evaluate(empty_matches(vegan_markers=["vegan"]), lang="en")
        ids = [p["id"] for p in result["packages"]]
        assert "halal" in ids
        assert "vegan" in ids

    def test_pork_no_halal_package(self):
        result = engine.evaluate(empty_matches(pork=["bacon"]))
        ids = [p["id"] for p in result["packages"]]
        assert "halal" not in ids

    def test_allergen_warning_package(self):
        result = engine.evaluate(empty_matches(allergens=["peanuts"]))
        ids = [p["id"] for p in result["packages"]]
        assert "allergen_warning" in ids

    def test_all_packages_have_required_fields(self):
        result = engine.evaluate(empty_matches(
            vegan_markers=["vegan"],
            bio_labels=["bio"],
            allergens=["soy"],
        ), lang="de")
        for pkg in result["packages"]:
            assert "id" in pkg
            assert "label" in pkg
            assert "icon" in pkg
            assert pkg["confidence"] in ("high", "medium")

    def test_packages_french(self):
        result = engine.evaluate(empty_matches(vegan_markers=["vegan"]), lang="fr")
        labels = {p["id"]: p["label"] for p in result["packages"]}
        assert labels.get("vegan") == "Végane"
        assert labels.get("halal") == "Halal"

    def test_packages_italian(self):
        result = engine.evaluate(empty_matches(vegan_markers=["vegan"]), lang="it")
        labels = {p["id"]: p["label"] for p in result["packages"]}
        assert labels.get("vegan") == "Vegano"

    def test_vegan_likely_medium_confidence(self):
        result = engine.evaluate(empty_matches())
        likely = next((p for p in result["packages"] if p["id"] == "vegan_likely"), None)
        assert likely is not None
        assert likely["confidence"] == "medium"

    def test_vegan_supersedes_vegan_likely(self):
        result = engine.evaluate(empty_matches(vegan_markers=["vegan"]))
        ids = [p["id"] for p in result["packages"]]
        assert "vegan" in ids
        assert "vegan_likely" not in ids
