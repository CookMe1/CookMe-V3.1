import sys
sys.path.insert(0, "backend")
from wikibooks_categories import from_categories
from wikibooks_parser import parse_recipe


def test_categories_set_cuisine_tags_and_exclusions():
    c = from_categories(["Indian recipes", "Halal recipes", "Inexpensive recipes", "Recipes for dessert", "Recipes using rice"])
    assert c["cuisine"] == "indian" and "halal" in c["tags"] and "budget" in c["tags"] and c["dessert"] and not c["exclude"]
    assert from_categories(["Nigerian recipes"])["cuisine"] == "african"
    assert from_categories(["Pakistani recipes"])["cuisine"] == "south_asian"
    assert from_categories(["Egyptian recipes"])["cuisine"] == "middle_eastern"
    assert from_categories(["Pet recipes"])["exclude"]
    assert from_categories(["Slow cooker recipes"])["tags"] == ["crockpot", "slow cooker"]


def test_parser_uses_categories_and_records_if_servings_were_stated():
    wt = ("{{recipesummary|category=|servings=6|time=1 hour|difficulty=2}}\nA good stew for a cold day, made simply.\n"
          "== Ingredients ==\n* 500 g beef\n* 2 onions\n* 1 tbsp oil\n== Procedure ==\n# Brown the beef.\n# Add onions.\n# Simmer for 1 hour.\n"
          "[[Category:African recipes]]\n[[Category:Halal recipes]]")
    r = parse_recipe("Cookbook:Test Stew", wt)
    assert r["cuisine"] == "african" and "halal" in r["tags"] and r["servings"] == 6 and r["servings_stated"] is True
    r2 = parse_recipe("Cookbook:Test Stew", wt.replace("servings=6|", ""))
    assert r2["servings"] == 4 and r2["servings_stated"] is False
    assert parse_recipe("Cookbook:X", wt + "\n[[Category:Pet recipes]]") is None
