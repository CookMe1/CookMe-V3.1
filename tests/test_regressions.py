import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
import os; os.environ.setdefault("JWT_SECRET", "x")
from meal_plan_builder import slot_kinds
from recipe_tagger import is_dessert
import pytest

def rec(title, n=8, tags=()):
    return {"title": title, "tags": list(tags), "ingredients": [{"item": f"thing{i}", "amount": "1"} for i in range(n)], "steps": ["Cook it well."] * 5}

def test_dessert_bars_not_a_meal():
    for t in ["Dark Chocolate Rocky Road Dessert Bars", "Salted Caramels", "Peanut Butter Bars"]:
        assert is_dessert(rec(t)), t
        assert "dinner" not in slot_kinds(rec(t)), t

def test_snacks_and_dips_not_a_meal():
    for t in ["Nacho chips", "Spiced nuts", "Party ideas roundup", "Padron peppers"]:
        assert "dinner" not in slot_kinds(rec(t, n=3)), t

def test_real_dinner_still_a_dinner():
    assert "dinner" in slot_kinds(rec("Chicken Tikka Masala", n=10))

def ings(*names): return [{"item": n, "amount": "1"} for n in names]

def test_pasta_matches_spaghetti_and_needs_two_pantry_items():
    pytest.importorskip('emergentintegrations')  # pantry routes import it; skipped where it isn't installed
    from routes.pantry_routes import _score_master, _pantry_groups
    groups = _pantry_groups(["pasta", "egg", "bacon"])
    ok, pct, matched, missing, used = _score_master(ings("Spaghetti", "Eggs", "Bacon", "Salt"), groups, "most", 1)
    assert ok and used == 3
    # a recipe that only uses one of three pantry items is not a match
    ok, *_ = _score_master(ings("Eggs", "Salt", "Oil"), groups, "most", 1)
    assert not ok
