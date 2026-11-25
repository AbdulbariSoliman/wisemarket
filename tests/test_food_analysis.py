# ============================================================
# WISEMARKET — FOOD ANALYSIS ACCURACY TESTS
# Full pipeline: IngredientParser -> OntologyRouter -> OntologyMatcher
# -> DecisionEngine, on REAL ingredient lists from Open Food Facts
# (data/open_food_facts/swiss_products_p1.json) plus a few Swiss-German
# label patterns. Expected values were checked by hand against the label.
# No database needed.
# ============================================================
import pytest

from backend.normalizer.ontology_loader import load_ontology
from backend.services.decision_engine import DecisionEngine
from backend.services.ingredient_parser import IngredientParser
from backend.services.ontology_matcher import OntologyMatcher
from backend.services.ontology_router import OntologyRouter

PARSER = IngredientParser()
ROUTER = OntologyRouter()
MATCHER = OntologyMatcher(load_ontology())
ENGINE = DecisionEngine()


def analyse(ingredients: str, category: str = "other") -> dict:
    parsed = PARSER.normalize(ingredients)
    matches = MATCHER.match(parsed, ROUTER.route(category))
    return ENGINE.evaluate(matches)


def not_vegan(v):
    return not v["vegan"] and not v["vegan_likely"]


# ── Real products (Open Food Facts) ───────────────────────────

NUTELLA = ("Sucre, huile de palme, NOISETTES 13%, cacao maigre 7,4%, LAIT écrémé en poudre 6,6%, "
           "LACTOSERUM en poudre, émulsifiants: lécithines [SOJA), vanilline. Sans gluten.")

GRANOLA = ("Farine de BLÉ 36%, chocolat au LAIT 27 % [sucre, pâte de cacao, beurre de cacao, lactosérum en "
           "poudre (de LAIT), LAIT écrémé en poudre, graisses végétales (karité, palme en proportion variable), "
           "BEURRE concentré, émulsifiants (lécithines de SOJA, E476), lactose (de LAIT), arôme], huile de palme, "
           "farine complète de BLE 12 %, sucre, sirop de sucre, poudres à lever (carbonates de sodium, carbonates "
           "d'ammonium), sel, correcteur d'acidité (acide citrique). Peut contenir : fruits à coque.")

DARK_CHOCOLATE = ("Sucre, pâte de cacao (Afrique de l'Ouest, Amérique du Sud), beurre de cacao, émulsifiant "
                  "(lécithine), arôme naturel de vanille de Madagascar. Cacao : 53% minimum. "
                  "Peut contenir : LAIT, FRUITS A COQUE.")

SOY_YOGURT = ("_Sojabasis_ (Wasser, geschälte _Sojabohnen_ (10,4%)], Kokosmilch (4,3%) (Kokosceme, Wasser), "
              "Zucker, Tricalciumcitrat, Säureregulatoren (Natriumcitrate, Citronensäure), Stabilisator (Pektine), "
              "natürliches Aroma, Meersalz, Vitamine (B12, D2), Joghurtkulturen (Str,thermophilus, L, bulgaricus).")

ALMOND_DRINK = ("Lait d'amandes 98% (eau 95,2%, amandes 2,8%), amidon de riz, arôme naturel d'amande, "
                "sel marin, stabilisants (gomme guar, gomme xanthane)")

BRIOCHE = ("Farine de blé 52%, sucre, beurre frais 10%, œufs entiers frais 8%, eau, crème fraîche 3%, sel, "
           "arômes naturels (contient alcool), levure, gluten de blé, eau de vie, protéines de lait(E471), "
           "levure désactivée, colorant (béta carotène)")

CRUESLY = ("_avoine_ complète (32%), _blé_ complet (18%), sirop de glucose, huile de tournesol, sucre, "
           "_amandes_ grillées (4,2%), _noisettes_ (4%), oligofructose, _noix de Pécan_ (1,5%), farine de _blé_, "
           "farine de riz, _noix du Brésil_ (1%), miel, arômes naturels, antioxydant (tocophérol).")

RYE_CRISPBREAD = ("Farine complète de SEIGLE (77 g*), farine de SEIGLE (28 g*), levure, sel. Peut contenir des "
                  "traces de LUPIN, LAIT, MOUTARDE, GRAINES DE SÉSAME et SOJA. *en g pour 100 g de produit.")


def test_nutella_contains_milk_and_palm_oil():
    v = analyse(NUTELLA, "snacks")
    assert not_vegan(v)
    assert v["vegetarian"]
    assert v["has_palm_oil"]
    assert v["allergen_warning"]


def test_granola_milk_chocolate_wheat_palm():
    v = analyse(GRANOLA, "bakery")
    assert not_vegan(v)
    assert v["vegetarian"]
    assert v["has_palm_oil"]
    assert not v["is_gluten_free"]


def test_dark_chocolate_with_milk_traces_stays_likely_vegan_but_warns():
    v = analyse(DARK_CHOCOLATE, "snacks")
    assert v["vegan_likely"]            # milk is only a "may contain" trace
    assert v["allergen_warning"]        # ...but allergic users are still warned


def test_soy_yogurt_cultures_are_not_dairy():
    v = analyse(SOY_YOGURT, "dairy_alternative")
    assert v["vegan_likely"]
    assert v["vegetarian"]


def test_almond_drink_is_plant_based():
    v = analyse(ALMOND_DRINK, "dairy_alternative")
    assert v["vegan_likely"]


def test_brioche_with_alcohol_is_not_halal():
    v = analyse(BRIOCHE, "bakery")
    assert not v["halal"]               # "contient alcool", "eau de vie"
    assert not_vegan(v)                 # butter, eggs, cream
    assert v["vegetarian"]


def test_opff_underscore_allergens_detect_wheat():
    v = analyse(CRUESLY, "bakery")
    assert not v["is_gluten_free"]      # _blé_ = wheat
    assert not_vegan(v)                 # honey
    assert v["vegetarian"]


def test_rye_crispbread_traces_do_not_change_diet_verdicts():
    v = analyse(RYE_CRISPBREAD, "bakery")
    assert v["vegan_likely"]
    assert v["vegetarian"]
    assert not v["is_gluten_free"]


# ── Swiss label patterns ──────────────────────────────────────

@pytest.mark.parametrize("ingredients", [
    "Zucker, Kakaobutter, Vollmilchpulver, Haselnüsse",
    "Zucker, Butterreinfett, Weizenmehl",
    "Zucker, Süssmolkenpulver, Kakaomasse",
])
def test_german_dairy_compounds_are_detected(ingredients):
    v = analyse(ingredients, "snacks")
    assert not_vegan(v)
    assert v["vegetarian"]


@pytest.mark.parametrize("ingredients", [
    "Zucker, Kakaobutter, Kakaomasse",
    "Wasser, Sojaeiweiß, Salz",
    "Zucker, Milchsäure, Pektin",
    "Lait de coco, sucre",
    "Crème de marrons, sucre",
])
def test_plant_look_alikes_are_not_animal(ingredients):
    v = analyse(ingredients)
    assert v["vegan_likely"]


def test_pork_gelatine_in_any_category():
    v = analyse("Sucre, sirop de glucose, gélatine de porc", "snacks")
    assert not v["halal"]
    assert not v["vegetarian"]
    assert not_vegan(v)


def test_beef_gelatine_is_not_vegetarian():
    v = analyse("Zucker, Glukosesirup, Rindergelatine", "snacks")
    assert not v["vegetarian"]


@pytest.mark.parametrize("ingredients", [
    "Zucker, Kakaobutter, palmölfrei",
    "Sucre, huile de tournesol, sans huile de palme",
    "Sugar, sunflower oil, palm oil free",
])
def test_palm_oil_free_claims_are_not_palm_oil(ingredients):
    assert not analyse(ingredients)["has_palm_oil"]


def test_sugar_alcohols_and_spirit_vinegar_are_not_alcohol():
    assert analyse("Zuckeralkohole (Maltit), Kakaobutter")["halal"]
    assert analyse("Eau, vinaigre d'alcool, graines de moutarde, sel")["halal"]


def test_sheep_milk_cheese_is_vegetarian_but_not_vegan():
    v = analyse("Tomato pulp, sunflower oil, Pecorino Romano PDO cheese (sheep's milk, salt, rennet)")
    assert v["vegetarian"]
    assert not_vegan(v)


def test_vegetable_butter_is_plant_based():
    v = analyse("CACAHUETES (86%), beurre végétal (sal, cacao), sucre, sel.")
    assert v["vegan_likely"]


def test_palm_written_without_oil_word_is_detected():
    v = analyse("Farine de blé, sucre, matières grasses végétales (palme, palmiste, colza), sel")
    assert v["has_palm_oil"]


def test_palm_sugar_is_not_palm_oil():
    assert not analyse("Sucre de palme, noix de coco")["has_palm_oil"]


# ── meat, fish, eggs and halal ───────────────────────────────────────

@pytest.mark.parametrize("ingredients, category", [
    ("Chicken breast", "meat"),
    ("Atlantic salmon (Salmo salar) 100%", "fish"),
    ("Filets de maquereau 70%, huile de colza, poivre, sel", "fish"),
    ("Hühnerei, Zucker, Weizenmehl", "bakery"),
    ("Vollei, Zucker", "bakery"),
])
def test_meat_fish_and_egg_are_never_vegan(ingredients, category):
    assert not_vegan(analyse(ingredients, category))


def test_fish_is_halal_but_not_vegetarian():
    v = analyse("Filets de maquereau 70%, huile de colza, sel", "fish")
    assert v["halal"] and not v["vegetarian"]


def test_meat_without_halal_label_is_not_halal():
    assert not analyse("Chicken breast", "meat")["halal"]


def test_meat_with_halal_label_is_halal():
    assert analyse("Halal chicken breast", "meat")["halal"]


def test_gelatine_without_halal_label_is_not_halal():
    assert not analyse("Zucker, Glukosesirup, Gelatine (Rind)", "snacks")["halal"]


def test_wine_grape_name_is_alcohol():
    assert not analyse("Cabernet Sauvignon", "beverages")["halal"]


@pytest.mark.parametrize("ingredients", ["Skyr, Zitrone, Zucker", "Mascarpone (Rahm)"])
def test_fresh_cheese_is_dairy(ingredients):
    assert not_vegan(analyse(ingredients, "dairy"))


def test_search_tags_follow_halal_in_product_name():
    from backend.services.product_tags import tags_from_ingredients
    assert not tags_from_ingredients("Chicken breast", "meat")["halal"]
    assert tags_from_ingredients("Chicken breast", "meat", name="Halal Chicken Breast 500g")["halal"]
    assert not tags_from_ingredients("Chicken breast", "meat")["vegan"]
    assert not tags_from_ingredients("Skyr, Zitrone", "dairy")["lactose_free"]


# ── real Open Food Facts spellings (found by the production backfill) ─

def test_ocr_capital_i_in_fish_name():
    v = analyse("65% _Alaska-SeeIachsfiIet_, _Weizenmehl_, Sonnenblumenöl, Wasser", "fish")
    assert not_vegan(v) and not v["vegetarian"]


def test_french_plural_fish_name():
    v = analyse("Filets de _maquereaux_ (60%), eau, vin blanc, sel", "fish")
    assert not_vegan(v) and not v["vegetarian"]


@pytest.mark.parametrize("ingredients", ["oeufs", "Œufs frais", "œufs"])
def test_oeuf_with_and_without_ligature(ingredients):
    assert not_vegan(analyse(ingredients))


def test_landwirtschaft_is_not_sheep():
    v = analyse("Amaranth* gepufft *aus biologischer Landwirtschaft")
    assert v["vegetarian"] and v["vegan_likely"]


def test_peux_contenir_is_a_trace():
    v = analyse("farine de maïs, huile de tournesol. Peux contenir du lait et du soja.")
    assert v["vegan_likely"]


def test_double_creme_is_dairy():
    assert not_vegan(analyse("double-crème, protéines lactiques, sel", "dairy"))


def test_froment_is_gluten():
    from backend.services.product_tags import tags_from_ingredients
    assert not tags_from_ingredients("sucre, farine de FROMENT 15,5%, sel", "bakery")["gluten_free"]


def test_unsupported_language_is_left_unchanged():
    from backend.services.product_tags import tags_from_ingredients
    croatian = ("19% kikiriki, 14% grožđice, šećer od šećerne trske, palmina mast, med, "
                "djelomično obrano mlijeko u prahu. Može sadržavati tragove jaja, lupine i soje.")
    assert tags_from_ingredients(croatian, "snacks") is None


def test_chopped_fruit_is_not_minced_meat():
    v = analyse("abricots secs hachés, noisettes hachées grillées, amandes")
    assert v["vegetarian"] and v["vegan_likely"]


# ── second production check ─────────────────────────────────────────

def _tags(ingredients, category="other", name=None):
    from backend.services.product_tags import tags_from_ingredients
    return tags_from_ingredients(ingredients, category, name)


@pytest.mark.parametrize("ingredients", [
    "TRIGO integral (50%), chocolate con LECHE (azúcar, manteca de cacao, LECHE entera en polvo), sal",
    "Sardinhas (peixe), Óleo de soja e Sal.",
    "Složení: tekutá káva (cukr), MLÉČNÁ čokoláda (cukr, plnotučné sušené MLÉKO), LAKTÓZA",
])
def test_spanish_portuguese_czech_are_left_unchanged(ingredients):
    assert _tags(ingredients) is None


def test_seitan_is_gluten():
    assert not _tags("SEITAN* 71 % (Wasser, WEIZENEIWEIß*), Zwiebeln, Speisesalz", "meat")["gluten_free"]


def test_ble_without_accent_is_gluten():
    assert not _tags("Sucre, farine de BLE, LAIT écrémé en poudre", "bakery")["gluten_free"]


def test_bonite_and_italian_plural_are_fish():
    assert not _tags("Bonite à ventre rayé (Katsuwonus pelamis), eau, sel", "fish")["vegetarian"]
    assert not _tags("Sgombri, olio di oliva, sale.", "fish")["vegetarian"]


def test_beer_in_product_name_is_alcohol():
    assert not _tags("eau de source, malt d'orge, houblon", "beverages",
                     "Hell Quöllfrisch Appenzeller Bier")["halal"]
    assert _tags("Wasser, Gerstenmalz, Hopfen", "beverages", "Alkoholfreies Bier 0.0")["halal"]
    assert _tags("Wasser, Zucker, Ingwer", "beverages", "Ginger Beer")["halal"]


def test_sans_lactose_yogurt_is_lactose_free():
    assert _tags("Yogourt partiellement écrémé, sans lactose, au lait pasteurisé, sucre", "dairy")["lactose_free"]


def test_decimal_commas_and_html_entities_are_cleaned():
    parsed = PARSER.normalize("cacao maigre 7,4%, LAIT écrémé en poudre 6,6%, &lt;1% son de blé, sel 0,5 g")
    assert parsed == ["cacao maigre", "lait écrémé en poudre", "son de blé", "sel"]


# ── products without an ingredient list (Migros): name-only tags ─────

@pytest.mark.parametrize("name, category, expected", [
    ("Butter und Chocolate Cookies", "snacks",
     {"vegan": False, "gluten_free": False, "lactose_free": False, "halal": None}),
    ("M-Classic · Petit Beurre · Chocolat au Lait", "snacks", {"vegan": False, "gluten_free": False}),
    ("LU · Barquette · Chocolat", "snacks",
     {"vegan": None, "vegetarian": None, "halal": None, "gluten_free": None}),
    ("Cornatur · Vegane Bratwurst", "plant_protein", {"vegan": True, "vegetarian": True, "halal": None}),
    ("Delikatess Geflügel Edelsalami", "meat", {"vegan": False, "vegetarian": False, "halal": False}),
    ("Halal Poulet Brust", "meat", {"halal": True, "vegetarian": False}),
    ("Feldschlösschen Bier", "beverages", {"halal": False}),
    ("Schär · Brot · glutenfrei", "bakery", {"gluten_free": True}),
    ("Migros High Protein · Milch · UHT, laktosefrei", "dairy", {"vegan": False, "lactose_free": True}),
    ("Bananen", "fresh_produce", {"vegan": True, "halal": True, "gluten_free": True}),
])
def test_name_only_tags_never_guess_safe(name, category, expected):
    from backend.services.product_tags import tags_from_name
    tags = tags_from_name(name, category)
    for key, value in expected.items():
        assert tags[key] is value, f"{name}: {key}={tags[key]}"


@pytest.mark.parametrize("category", ["meat", "dairy", None])
def test_eggs_filed_under_meat_are_still_vegetarian(category):
    from backend.services.product_tags import tags_from_name
    for name in ("Oeufs", "Eier aus Freilandhaltung"):
        tags = tags_from_name(name, category)
        assert tags["vegan"] is False
        assert tags["vegetarian"] is not False and tags["halal"] is not False


@pytest.mark.parametrize("name", ["Paulaner Weissbier", "Feldschlösschen Lagerbier", "Rotwein Merlot"])
def test_compound_beer_and_wine_names_are_not_halal(name):
    from backend.services.product_tags import tags_from_ingredients, tags_from_name
    assert tags_from_name(name, "beverages")["halal"] is False
    assert tags_from_ingredients("Wasser, Gerstenmalz, Hopfen, Hefe", "beverages", name)["halal"] is False


def test_schwein_is_not_wine():
    from backend.services.product_tags import _ALCOHOL_NAME
    assert not _ALCOHOL_NAME.search("schweinsbratwurst")
