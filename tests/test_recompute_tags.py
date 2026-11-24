"""The backfill only tightens tags automatically (see scripts/recompute_tags.py)."""
import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "recompute_tags", Path(__file__).resolve().parents[1] / "scripts" / "recompute_tags.py")
recompute = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(recompute)


@pytest.mark.parametrize("key, old, new, relaxing", [
    ("halal", False, True, True),          # not halal -> halal: needs review
    ("halal", True, False, False),         # halal -> not halal: always applied
    ("gluten_free", False, True, True),
    ("vegan", True, False, False),
    ("palm_oil", True, False, True),       # palm oil found -> not found: needs review
    ("palm_oil", None, False, False),      # no previous value: applied
    ("lactose_free", None, True, False),
])
def test_is_relaxing(key, old, new, relaxing):
    assert recompute.is_relaxing(key, old, new) is relaxing
