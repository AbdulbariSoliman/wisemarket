PATH = "backend/api/routes/products.py"


def replace_exact(content, before, after, label):
    if before not in content:
        print(f"  SKIP/WARN [{label}]: expected text not found.")
        return content, False
    if content.count(before) > 1:
        print(f"  WARN [{label}]: text appears more than once - manual check needed.")
        return content, False
    print(f"  OK [{label}]")
    return content.replace(before, after, 1), True


with open(PATH, "r", encoding="utf-8") as f:
    content = f.read()

before_import = "from fastapi import APIRouter"
after_import = (
    "from backend.services.ingredient_parser import parse_ingredients\n"
    "from backend.services.ontology_router import get_relevant_groups\n"
    "from backend.services.ontology_matcher import match_terms\n"
    "from backend.services.decision_engine import evaluate_product\n"
    "from fastapi import APIRouter"
)
content, ok1 = replace_exact(content, before_import, after_import, "add decision engine imports")

before_block = '''            unified = {
                "unified_id":       u.get("unified_id"),
                "name_en":          u.get("canonical_name_en"),
                "name_de":          u.get("canonical_name_de"),
                "brand":            u.get("canonical_brand"),
                "category":         u.get("canonical_category"),
                "image_url":        u.get("canonical_image_url"),
                "ingredients_raw":  u.get("canonical_ingredients_raw"),
                "nutrition":        u.get("canonical_nutrition"),
                "allergens":        u.get("allergens"),
                "field_sources":    u.get("field_sources") or {},
            }'''

after_block = '''            computed_tags = None
            try:
                raw_ing = u.get("canonical_ingredients_raw")
                cat = u.get("canonical_category")
                if raw_ing:
                    parsed = parse_ingredients(raw_ing)
                    groups = get_relevant_groups(cat)
                    matches = match_terms(parsed, groups)
                    computed_tags = evaluate_product(matches, cat)
            except Exception:
                computed_tags = None

            unified = {
                "unified_id":       u.get("unified_id"),
                "name_en":          u.get("canonical_name_en"),
                "name_de":          u.get("canonical_name_de"),
                "brand":            u.get("canonical_brand"),
                "category":         u.get("canonical_category"),
                "image_url":        u.get("canonical_image_url"),
                "ingredients_raw":  u.get("canonical_ingredients_raw"),
                "nutrition":        u.get("canonical_nutrition"),
                "allergens":        u.get("allergens"),
                "ontology_tags":    computed_tags,
                "field_sources":    u.get("field_sources") or {},
            }'''

content, ok2 = replace_exact(content, before_block, after_block, "compute ontology_tags via decision engine")

if ok1 and ok2:
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("\nBoth changes applied. File saved.")
else:
    print("\nOne or more changes NOT applied (see SKIP/WARN above). File NOT saved.")