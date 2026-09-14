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

bad_imports = (
    "from backend.services.ingredient_parser import parse_ingredients\n"
    "from backend.services.ontology_router import get_relevant_groups\n"
    "from backend.services.ontology_matcher import match_terms\n"
    "from backend.services.decision_engine import evaluate_product\n"
    "from fastapi import APIRouter"
)
if bad_imports in content:
    content = content.replace(bad_imports, "from fastapi import APIRouter", 1)
    print("  Removed previous incorrect imports.")

before_fastapi_import = "from fastapi import APIRouter"
after_fastapi_import = "from fastapi import APIRouter, Request"
content, ok1 = replace_exact(content, before_fastapi_import, after_fastapi_import, "add Request import")

before_sig = '''def get_product(
    gtin: str,
    store: Optional[str] = Query(None),
    lang: Literal["en", "de", "fr", "it"] = "en",'''

after_sig = '''def get_product(
    request: Request,
    gtin: str,
    store: Optional[str] = Query(None),
    lang: Literal["en", "de", "fr", "it"] = "en",'''

content, ok2 = replace_exact(content, before_sig, after_sig, "add request param to get_product")

old_wrong_block = '''            computed_tags = None
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

            unified = {'''

new_correct_block = '''            computed_tags = None
            try:
                raw_ing = u.get("canonical_ingredients_raw")
                cat = u.get("canonical_category") or "other"
                if raw_ing:
                    parsed_ingredients = request.app.state.parser.normalize(raw_ing)
                    groups = request.app.state.router.route(cat)
                    matches = request.app.state.matcher.match(parsed_ingredients, groups)
                    computed_tags = request.app.state.decision_engine.evaluate(matches, lang=lang)
            except Exception:
                computed_tags = None

            unified = {'''

if old_wrong_block in content:
    content, ok3 = replace_exact(content, old_wrong_block, new_correct_block, "fix computed_tags block (v2)")
else:
    before_unified_only = '''            unified = {'''
    content, ok3 = replace_exact(content, before_unified_only, new_correct_block, "insert computed_tags block (fresh)")

if ok1 and ok2 and ok3:
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("\nAll changes applied. File saved.")
else:
    print("\nOne or more changes NOT applied (see SKIP/WARN above). File NOT saved.")