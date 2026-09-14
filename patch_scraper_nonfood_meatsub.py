# ============================================================
# WISEMARKET - PATCH: Bug A (non-food items getting dietary
# tags) and Bug B (meat substitutes miscategorized as meat)
# ============================================================

PATH = "backend/etl/scraper_migros.py"


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

# --- Bug B: meat-substitute override in map_category() ---
before_map_category = '''def map_category(breadcrumb: list) -> str:
    for crumb in breadcrumb:
        name = crumb.get("name", "")
        for key, cat in CATEGORY_MAP.items():
            if key.lower() in name.lower():
                return cat
    return "other"'''

after_map_category = '''SUBSTITUTE_MARKERS = [
    "ersatz", "fleischersatz", "vegan", "vegi", "pflanzlich",
    "plant-based", "plant based", "veggie", "soja", "tofu", "seitan",
]


def map_category(breadcrumb: list) -> str:
    breadcrumb_text = " ".join(c.get("name", "") for c in breadcrumb).lower()
    matched_cat = None
    for crumb in breadcrumb:
        name = crumb.get("name", "")
        for key, cat in CATEGORY_MAP.items():
            if key.lower() in name.lower():
                matched_cat = cat
                break
        if matched_cat:
            break
    if matched_cat in ("meat", "fish") and any(m in breadcrumb_text for m in SUBSTITUTE_MARKERS):
        return "plant_protein"
    return matched_cat or "other"'''

content, ok1 = replace_exact(content, before_map_category, after_map_category, "Bug B: meat-substitute override")

# --- Bug A: no dietary tags for uncategorized ("other") products ---
before_gate = '''def build_ontology_tags(name: str, breadcrumb: list) -> dict:
    cat = map_category(breadcrumb)
    name_lower = name.lower()'''

after_gate = '''def build_ontology_tags(name: str, breadcrumb: list) -> dict:
    cat = map_category(breadcrumb)
    name_lower = name.lower()

    # Bug A fix: if the product doesn't resolve to a known food
    # category, don't claim any dietary/religious safety tags at
    # all - "uncategorized" must mean unknown, never "safe."
    if cat == "other":
        return {
            "halal": None, "vegetarian": None, "vegan": None,
            "gluten_free": None, "lactose_free": None,
            "organic": False, "regional": False,
            "is_bio": False, "is_regional": False,
        }'''

content, ok2 = replace_exact(content, before_gate, after_gate, "Bug A: gate dietary tags on known food category")

if ok1 and ok2:
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("\nBoth changes applied. File saved.")
else:
    print("\nOne or more changes NOT applied (see SKIP/WARN above). File NOT saved.")