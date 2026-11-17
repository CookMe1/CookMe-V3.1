"""Offline tests for the ingredient dictionary and automatic tagger."""
import pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "backend"))
import ingredient_dictionary as d
from recipe_tagger import auto_tag


def test_dictionary_translates_common_words():
    for word, english in [("pollo", "chicken"), ("Zwiebeln", "onion"), ("oignon", "onion"), ("aceite de oliva", "olive oil"),
                          ("champiñones", "mushrooms"), ("manteiga", "butter"), ("Kartoffeln", "potato")]:
        assert d.to_english(word) == english, word


def test_dictionary_phrase_and_unknown():
    assert d.to_english("pechuga de pollo deshuesada") == "chicken breast"
    assert d.to_english("dragon fruit") is None


def test_to_language():
    assert d.to_language("chicken", "es") == "pollo"
    assert d.to_language("onion", "de") == "zwiebel"


def test_tagger_diet_and_cuisine():
    veg = auto_tag({"title": "Vegan Chickpea Curry", "ingredients": [{"item": "chickpeas"}, {"item": "coconut milk"}, {"item": "curry powder"}], "steps": ["a"]})
    assert "vegan" in veg["tags"] and "vegetarian" in veg["tags"] and veg["cuisine"] == "indian"
    meat = auto_tag({"title": "Beef stew", "ingredients": [{"item": "beef"}, {"item": "carrots"}], "steps": ["a"] * 8})
    assert "vegetarian" not in meat["tags"] and "vegan" not in meat["tags"] and "one pot" in meat["tags"]


def test_tagger_keeps_existing_and_never_tags_allergens():
    r = auto_tag({"title": "Cake", "ingredients": ["flour", "milk"], "steps": ["a"], "tags": ["mine"]})
    assert "mine" in r["tags"] and "gluten-free" not in r["tags"] and "dairy-free" not in r["tags"]
