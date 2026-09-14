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

before_block = '''            computed_tags = None
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

after_block = '''            computed_tags = None
            try:
                raw_ing = u.get("canonical_ingredients_raw")
                cat = u.get("canonical_category") or "other"
                if raw_ing:
                    parsed_ingredients = request.app.state.parser.normalize(raw_ing)
                    groups = request.app.state.router.route(cat)
                    matches = request.app.state.matcher.match(parsed_ingredients, groups)

                    try:
                        off_resp = (
                            supabase.table("products")
                            .select("ontology_tags")
                            .eq("gtin", gtin)
                            .eq("store", "open_food_facts")
                            .limit(1)
                            .execute()
                        )
                        off_tags = (off_resp.data[0].get("ontology_tags") or {}) if off_resp.data else {}
                    except Exception:
                        off_tags = {}

                    if off_tags.get("vegan") is True:
                        matches.setdefault("vegan_markers", [])
                        if "off:verified" not in matches["vegan_markers"]:
                            matches["vegan_markers"].append("off:verified")

                    if off_tags.get("gluten_free") is True:
                        if not matches.get("coeliac_triggers"):
                            matches.setdefault("gluten_free_labels", [])
                            if "off:verified" not in matches["gluten_free_labels"]:
                                matches["gluten_free_labels"].append("off:verified")

                    if off_tags.get("lactose_free") is True:
                        matches.setdefault("lactose_free_labels", [])
                        if "off:verified" not in matches["lactose_free_labels"]:
                            matches["lactose_free_labels"].append("off:verified")

                    computed_tags = request.app.state.decision_engine.evaluate(matches, lang=lang)
            except Exception:
                computed_tags = None

            unified = {'''

content, ok = replace_exact(content, before_block, after_block, "inject verified OFF facts into matches")

if ok:
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("\nChange applied. File saved.")
else:
    print("\nChange NOT applied (see SKIP/WARN above). File NOT saved.")