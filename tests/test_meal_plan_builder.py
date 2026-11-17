"""Offline tests: recipe-based meal plans (no AI)."""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
from meal_plan_builder import build_plan, slot_kinds, skeleton

DATA = json.load(open(ROOT / "data" / "master_recipes.json", encoding="utf-8"))
TAGS = {r["recipe_id"]: set(r["tags"]) for r in DATA}


def test_full_week_no_repeats():
    days, _ = build_plan("2026-11-23", DATA, seed="a")
    assert [d["day_name"] for d in days][0] == "Monday" and len(days) == 7
    ids = [d[s]["recipe_id"] for d in days for s in ("breakfast", "lunch", "dinner") if d[s]]
    assert len(ids) == 21 and len(set(ids)) == 21


def test_vegetarian_plan_only_vegetarian():
    days, _ = build_plan("2026-11-23", DATA, diets=["vegetarian"], seed="b")
    for d in days:
        for s in ("breakfast", "lunch", "dinner"):
            assert "vegetarian" in TAGS[d[s]["recipe_id"]]


def test_unsupported_restriction_falls_back_to_ai():
    assert build_plan("2026-11-23", DATA, diets=["gluten-free"]) is None


def test_desserts_and_sauces_are_not_meals():
    assert slot_kinds({"title": "Chocolate Cake", "tags": ["dessert"]}) == set()
    assert slot_kinds({"title": "Korean Barbecue Sauce", "tags": []}) == set()
    assert slot_kinds({"title": "Greek Salad", "tags": []}) == {"lunch"}


def test_near_duplicate_titles_match():
    assert skeleton("Fettucine Alfredo") == skeleton("Fettuccine Alfredo")


def test_different_seed_gives_different_plan():
    a, _ = build_plan("2026-11-23", DATA, seed="x")
    b, _ = build_plan("2026-11-23", DATA, seed="y")
    assert a != b
