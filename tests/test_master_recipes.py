"""Offline checks on data/master_recipes.json (no server or database needed).
Run from the project root: python -m pytest tests/test_master_recipes.py"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
DATA = json.load(open(ROOT / "data" / "master_recipes.json", encoding="utf-8"))
USER_FIELDS = {"uploader_id", "uploader_name", "password_hash", "email"}


def test_has_recipes():
    assert len(DATA) > 1000


def test_no_user_data():
    for r in DATA:
        assert r["user_id"] == "system_seeder"
        assert not (USER_FIELDS & set(r))
        assert r["favorited_by"] == [] and r["hidden_by"] == [] and r["gallery_images"] == []
        assert r["likes_count"] == 0 and r["saves_count"] == 0


def test_unique_ids_and_titles():
    assert len({r["recipe_id"] for r in DATA}) == len(DATA)
    assert len({r["title"].strip().lower() for r in DATA}) == len(DATA)


def test_every_recipe_has_content_and_valid_image():
    for r in DATA:
        assert r["ingredients"] and r["steps"]
        img = r.get("image")
        assert img is None or img.startswith(("http", "data:image/"))


def test_cooking_types_present():
    tags = {t for r in DATA for t in r["tags"]}
    assert {"quick", "student", "one pot", "air fryer"} <= tags


def test_matches_recipe_model():
    from models import Recipe
    for r in DATA:
        Recipe(**r)


def test_vegetarian_and_vegan_tags_are_safe():
    import re
    meat = re.compile(r"beef|pork|lamb|chicken|bacon|sausage|prawn|shrimp|salmon|tuna|anchov", re.I)
    dairy_egg = re.compile(r"\bmilk|butter|cheese|cream|\beggs?\b|honey", re.I)
    for r in DATA:
        text = " ".join(str(i.get("item", "")) for i in r["ingredients"] if isinstance(i, dict))
        if "vegetarian" in r["tags"]:
            assert not meat.search(text), r["title"]
        if "vegan" in r["tags"]:
            assert not dairy_egg.search(text), r["title"]


def test_no_unsafe_allergy_tags():
    tags = {t for r in DATA for t in r["tags"]}
    assert "gluten-free" not in tags and "dairy-free" not in tags
