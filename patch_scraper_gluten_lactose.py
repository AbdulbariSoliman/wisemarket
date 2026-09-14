# ============================================================
# WISEMARKET - PATCH: fix absence-based dietary claims in
# build_ontology_tags() (scraper_migros.py)
#
# Problem: gluten_free and lactose_free were True by DEFAULT
# unless specific keywords appeared in the product name/category
# - meaning "we didn't check" was being reported as "verified
# safe." These now return None (unknown) instead of a
# false-positive True when there's no real positive signal.
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

before = '''    return {
        "halal":        halal,
        "vegetarian":   cat not in ["meat","fish"] and not has_pork,
        "vegan":        cat not in ["meat","fish","dairy"] and not has_pork,
        "gluten_free":  not any(x in name_lower for x in ["brot","pasta","mehl","weizen","gerste","dinkel"]),
        "lactose_free": cat != "dairy",
        "organic":      is_bio,
        "regional":     is_regional,
        "is_bio":       is_bio,
        "is_regional":  is_regional,
    }'''

after = '''    explicit_gluten_free = any(x in name_lower for x in
        ["glutenfrei","gluten-frei","gluten free","sans gluten","senza glutine"])
    contains_gluten_words = any(x in name_lower for x in
        ["brot","pasta","mehl","weizen","gerste","dinkel","nudeln","kuchen","gebäck","teig"])

    explicit_lactose_free = any(x in name_lower for x in
        ["laktosefrei","laktose-frei","lactose free","sans lactose","senza lattosio"])

    if explicit_gluten_free:
        gluten_free_tag = True
    elif contains_gluten_words:
        gluten_free_tag = False
    else:
        gluten_free_tag = None

    if explicit_lactose_free:
        lactose_free_tag = True
    elif cat == "dairy":
        lactose_free_tag = False
    else:
        lactose_free_tag = None

    return {
        "halal":        halal,
        "vegetarian":   cat not in ["meat","fish"] and not has_pork,
        "vegan":        cat not in ["meat","fish","dairy"] and not has_pork,
        "gluten_free":  gluten_free_tag,
        "lactose_free": lactose_free_tag,
        "organic":      is_bio,
        "regional":     is_regional,
        "is_bio":       is_bio,
        "is_regional":  is_regional,
    }'''

content, ok = replace_exact(content, before, after, "fix gluten_free/lactose_free absence-based claims")

if ok:
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("\nChange applied. File saved.")
else:
    print("\nChange NOT applied (see SKIP/WARN above). File NOT saved.")