# ============================================================
# WISEMARKET - PATCH: fix multi-word search
#
# Before: "hackfleisch pasta tomaten" was matched as one literal
# phrase against the product name - never matches anything real.
#
# After: splits the query into individual words and matches
# products whose name contains ANY of them (OR), which is what
# users actually expect from a multi-word search (e.g. searching
# ingredients for a recipe).
# ============================================================

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

before = '''    if q:
        name_col = f"name_{lang}" if lang in ("en", "de", "fr", "it") else "name_en"
        query = query.ilike(name_col, f"%{q}%")'''

after = '''    if q:
        name_col = f"name_{lang}" if lang in ("en", "de", "fr", "it") else "name_en"
        words = [w for w in q.strip().split() if w]
        if len(words) <= 1:
            # single word - simple substring match, unchanged behavior
            query = query.ilike(name_col, f"%{q}%")
        else:
            # multi-word query - match products whose name contains
            # ANY of the individual words (e.g. recipe-ingredient style
            # searches like "hackfleisch pasta tomaten")
            or_clause = ",".join(f"{name_col}.ilike.%{w}%" for w in words)
            query = query.or_(or_clause)'''

content, ok = replace_exact(content, before, after, "fix multi-word search to match ANY word")

if ok:
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("\nChange applied. File saved.")
else:
    print("\nChange NOT applied (see SKIP/WARN above). File NOT saved.")