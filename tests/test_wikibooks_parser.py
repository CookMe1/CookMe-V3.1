import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from wikibooks_parser import parse_recipe, split_ingredient, clean_markup

SAMPLE = """{{recipesummary|Category=Bread recipes|Difficulty=2|Servings=4|Time=1 hour 15 minutes|Image=[[File:Soda bread.jpg|300px]]}}
{{recipe}}

'''Irish soda bread''' is a quick bread that uses [[w:Baking soda|baking soda]] instead of yeast. It needs no kneading.

== Ingredients ==
* 4 cups [[Cookbook:Flour|flour]]
* 1&nbsp;1/2 [[Cookbook:Teaspoon|tsp]] [[Cookbook:Salt|salt]]
* 1 3/4 cups [[Cookbook:Buttermilk|buttermilk]]<ref>or sour milk</ref>
* 2 to 3 tbsp butter
* Raisins, as desired

== Procedure ==
# Preheat the [[Cookbook:Oven|oven]] to 425°F.
# Mix the dry ingredients, then stir in the buttermilk.
# Shape into a round and bake for 35 minutes.

== Notes, tips, and variations ==
* Add caraway.

[[Category:Bread recipes]]
"""

def test_parses_full_recipe():
    r = parse_recipe("Cookbook:Irish Soda Bread", SAMPLE)
    assert r["title"] == "Irish Soda Bread" and r["servings"] == 4 and r["difficulty"] == "Easy"
    assert r["cook_time"] == "1 hr 15 min" and r["tags"] == ["Bread"]
    assert [i["item"] for i in r["ingredients"]][:3] == ["flour", "salt", "buttermilk"]
    assert r["ingredients"][0]["amount"] == "4 cups" and r["ingredients"][1]["amount"].startswith("1 1/2")
    assert r["ingredients"][3] == {"item": "butter", "amount": "2 to 3 tbsp"}
    assert r["ingredients"][4] == {"item": "Raisins, as desired", "amount": ""}
    assert len(r["steps"]) == 3 and r["steps"][0].startswith("Preheat the oven")
    assert "baking soda" in r["description"] or "quick bread" in r["description"]
    assert r["source_url"] == "https://en.wikibooks.org/wiki/Cookbook:Irish_Soda_Bread" and r["source_license"] == "CC BY-SA 4.0"
    assert r["wikibooks_image"] == "Soda bread.jpg"
    assert "[[" not in str(r) and "{{" not in str(r) and "<ref" not in str(r)

def test_not_a_recipe_returns_none():
    assert parse_recipe("Cookbook:Flour", "Flour is a powder.\n== History ==\nOld.") is None
    assert parse_recipe("Cookbook:X", "#REDIRECT [[Cookbook:Y]]") is None
    assert parse_recipe("Cookbook:Empty", "== Ingredients ==\n* 1 egg\n\n== Procedure ==\n") is None

def test_plain_paragraph_method():
    wt = "== Ingredients ==\n* 2 eggs\n* 1 cup milk\n== Procedure ==\nWhisk the eggs and milk together until smooth and pour into a hot pan.\n\nCook until set, about two minutes."
    assert len(parse_recipe("Cookbook:Omelette", wt)["steps"]) == 2

def test_split_ingredient_and_markup():
    assert split_ingredient("½ cup [[sugar]]") == {"item": "sugar", "amount": "½ cup"}
    assert split_ingredient("3 large eggs") == {"item": "large eggs", "amount": "3"}
    assert clean_markup("'''bold''' and [http://x.org link] {{template}} text") == "bold and link text"
