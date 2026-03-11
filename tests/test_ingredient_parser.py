from backend.services.ingredient_parser import IngredientParser


def test_simple_ingredients():
    parser = IngredientParser()
    result = parser.normalize("Milk, Sugar, Salt")
    assert result == ["milk", "sugar", "salt"]


def test_nested_parentheses():
    parser = IngredientParser()
    result = parser.normalize(
        "Milk chocolate (sugar, cocoa butter, milk powder, E 322), hazelnuts (10%), salt."
    )
    assert result == [
        "milk chocolate",
        "hazelnuts",
        "salt",
        "sugar",
        "cocoa butter",
        "milk powder",
        "e322",
    ]


def test_semicolon_split():
    parser = IngredientParser()
    result = parser.normalize("Water; sugar; lemon juice; flavouring")
    assert result == ["water", "sugar", "lemon juice", "flavouring"]


def test_e_number_variants():
    parser = IngredientParser()
    result = parser.normalize("Emulsifier (E 322), stabilizer (E-471)")
    assert result == ["emulsifier", "stabilizer", "e322", "e471"]


def test_empty_input():
    parser = IngredientParser()
    assert parser.normalize("") == []
    assert parser.normalize("   ") == []