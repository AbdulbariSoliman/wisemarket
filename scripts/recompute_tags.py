# ============================================================
# WISEMARKET — RECOMPUTE STORED PRODUCT TAGS (one-time backfill)
# ============================================================
# Re-runs the ingredient analysis for every product that has an
# ingredient list and updates its `ontology_tags` (used by the search
# filters), so stored tags match /analyze/{gtin}.
#
# Usage (from the repo root):
#   python scripts/recompute_tags.py            # preview only, changes nothing
#   python scripts/recompute_tags.py --apply    # write the new tags
#   python scripts/recompute_tags.py --store open_food_facts --apply
#   python scripts/recompute_tags.py --apply --allow-relax   # also loosen tags
#   python scripts/recompute_tags.py --show 7610900027392 3017620422003
#                                               # explain single products
# ============================================================
import argparse
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv  # noqa: E402
from backend.config.settings import ENV_FILE  # noqa: E402
from backend.api.db import get_supabase_client  # noqa: E402
from backend.services.product_tags import tags_from_ingredients, tags_from_name  # noqa: E402

load_dotenv(dotenv_path=ENV_FILE)

PAGE = 500
KEYS = ("vegan", "vegetarian", "halal", "gluten_free", "lactose_free", "palm_oil")

# The "careful" value of each tag. Changing a tag TOWARDS this value is always
# applied. Changing it AWAY from it (e.g. "not halal" -> "halal", "contains
# gluten" -> "gluten-free") is only listed for review, unless --allow-relax,
# because wrongly calling a product safe is the harmful mistake.
SAFE_VALUE = {"vegan": False, "vegetarian": False, "halal": False,
              "gluten_free": False, "lactose_free": False, "palm_oil": True}


def is_relaxing(key: str, old, new) -> bool:
    return old == SAFE_VALUE[key] and new != SAFE_VALUE[key]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="write changes (default: preview only)")
    ap.add_argument("--store", help="only this store, e.g. open_food_facts")
    ap.add_argument("--allow-relax", action="store_true",
                    help="also apply changes that loosen a tag (e.g. not halal -> halal)")
    ap.add_argument("--show", nargs="+", metavar="GTIN",
                    help="print ingredients and old/new tags for these products, change nothing")
    args = ap.parse_args()

    sb = get_supabase_client()
    if args.show:
        show(sb, args.show)
        return
    changes = collections.Counter()
    held = collections.Counter()
    examples = collections.defaultdict(list)
    counts = {"ingredients": 0, "name": 0}
    updated = 0

    # Pass 1: products with an ingredient list -> full analysis.
    # Pass 2: products without one (e.g. Migros) -> name-only rules, which
    #         say "unknown" instead of guessing "vegan" / "halal" / "gluten-free".
    for source in ("ingredients", "name"):
        offset = 0
        while True:
            q = (sb.table("products")
                   .select("id, gtin, store, name_en, name_de, category, ingredients_raw, ontology_tags")
                   .order("id")
                   .range(offset, offset + PAGE - 1))
            q = q.not_.is_("ingredients_raw", "null") if source == "ingredients" \
                else q.is_("ingredients_raw", "null")
            if args.store:
                q = q.eq("store", args.store)
            rows = q.execute().data
            if not rows:
                break
            offset += PAGE

            for row in rows:
                counts[source] += 1
                name = row.get("name_de") or row.get("name_en")
                if source == "ingredients":
                    new = tags_from_ingredients(row.get("ingredients_raw") or "", row.get("category"),
                                                row.get("name_en"))
                    if new is None:
                        # Ingredients in a language we can't read: judge by the
                        # name only, so old "safe" guesses become "unknown"
                        new = tags_from_name(name, row.get("category"))
                else:
                    new = tags_from_name(name, row.get("category"))
                if not new:
                    continue
                old = row.get("ontology_tags") or {}
                diff = {}
                for k in KEYS:
                    if old.get(k) == new.get(k):
                        continue
                    change = f"{k}: {old.get(k)} -> {new.get(k)}"
                    if is_relaxing(k, old.get(k), new.get(k)) and not args.allow_relax:
                        held[change] += 1          # keep the old, careful value
                    else:
                        diff[k] = new.get(k)
                        changes[change] += 1
                    example = f"{row['gtin']} {(row.get('name_en') or name or '')[:35]}"
                    if len(examples[change]) < 3 and not any(e.startswith(row["gtin"]) for e in examples[change]):
                        examples[change].append(example)
                if not diff:
                    continue
                if args.apply:
                    sb.table("products").update({"ontology_tags": {**old, **diff}}).eq("id", row["id"]).execute()
                updated += 1

    mode = "UPDATED" if args.apply else "WOULD UPDATE (preview)"
    print(f"Scanned {counts['ingredients']} products with ingredients and "
          f"{counts['name']} without — {mode}: {updated}")
    for change, n in changes.most_common():
        print(f"  {n:6}  {change:28}  e.g. " + "; ".join(examples[change]))
    if held:
        print("\nNOT applied - these would loosen a tag (check with --show, "
              "apply with --allow-relax):")
        for change, n in held.most_common():
            print(f"  {n:6}  {change:28}  e.g. " + "; ".join(examples[change]))
    if not args.apply and updated:
        print("\nRun again with --apply to write these changes.")


def show(sb, gtins) -> None:
    rows = (sb.table("products")
              .select("gtin, store, name_en, name_de, category, ingredients_raw, ontology_tags")
              .in_("gtin", gtins).execute().data)
    if not rows:
        print("No products found for:", " ".join(gtins))
    seen = set()
    for row in rows:
        if row["gtin"] in seen:          # same product in several stores
            continue
        seen.add(row["gtin"])
        old = row.get("ontology_tags") or {}
        if row.get("ingredients_raw"):
            new = tags_from_ingredients(row["ingredients_raw"], row.get("category"), row.get("name_en")) \
                or tags_from_name(row.get("name_de") or row.get("name_en"), row.get("category"))
        else:
            new = tags_from_name(row.get("name_de") or row.get("name_en"), row.get("category"))
        print(f"\n{row['gtin']}  {row.get('name_en')}  [{row.get('category')}]")
        print(f"  ingredients: {(row.get('ingredients_raw') or '').strip()[:600]}")
        for k in KEYS:
            mark = "  <- changes" if old.get(k) != new.get(k) else ""
            print(f"  {k:13} {str(old.get(k)):5} -> {new.get(k)}{mark}")


if __name__ == "__main__":
    main()
