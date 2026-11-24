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
# ============================================================
import argparse
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv  # noqa: E402
from backend.config.settings import ENV_FILE  # noqa: E402
from backend.api.db import get_supabase_client  # noqa: E402
from backend.services.product_tags import tags_from_ingredients  # noqa: E402

load_dotenv(dotenv_path=ENV_FILE)

PAGE = 500
KEYS = ("vegan", "vegetarian", "halal", "gluten_free", "lactose_free", "palm_oil")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="write changes (default: preview only)")
    ap.add_argument("--store", help="only this store, e.g. open_food_facts")
    args = ap.parse_args()

    sb = get_supabase_client()
    changes = collections.Counter()
    examples = collections.defaultdict(list)
    scanned = updated = 0
    offset = 0

    while True:
        q = (sb.table("products")
               .select("id, gtin, store, name_en, category, ingredients_raw, ontology_tags")
               .not_.is_("ingredients_raw", "null")
               .order("id")
               .range(offset, offset + PAGE - 1))
        if args.store:
            q = q.eq("store", args.store)
        rows = q.execute().data
        if not rows:
            break
        offset += PAGE

        for row in rows:
            scanned += 1
            new = tags_from_ingredients(row.get("ingredients_raw") or "", row.get("category"))
            if not new:
                continue
            old = row.get("ontology_tags") or {}
            diff = {k: new[k] for k in KEYS if old.get(k) != new[k]}
            if not diff:
                continue
            for k, v in diff.items():
                change = f"{k}: {old.get(k)} -> {v}"
                changes[change] += 1
                if len(examples[change]) < 3:
                    examples[change].append(f"{row['gtin']} {(row.get('name_en') or '')[:35]}")
            if args.apply:
                sb.table("products").update({"ontology_tags": {**old, **new}}).eq("id", row["id"]).execute()
            updated += 1

    mode = "UPDATED" if args.apply else "WOULD UPDATE (preview)"
    print(f"Scanned {scanned} products with ingredients — {mode}: {updated}")
    for change, n in changes.most_common():
        print(f"  {n:6}  {change:28}  e.g. " + "; ".join(examples[change]))
    if not args.apply and updated:
        print("\nRun again with --apply to write these changes.")


if __name__ == "__main__":
    main()
