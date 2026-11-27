import sys
sys.path.insert(0, "backend"); sys.path.insert(0, "scripts")
import modernise_old as m


def rec(title, ings, steps, url="https://www.gutenberg.org/ebooks/1"):
    return {"title": title, "category": "snack", "tags": [], "source_url": url,
            "ingredients": [{"amount": a, "item": i} for a, i in ings], "steps": steps}


def test_wording_is_modernised_without_changing_the_recipe():
    s = m.tidy_step("put the catsup on the range for twenty-four minutes with two teaspoonfuls of salt in a quick oven")
    assert s.startswith("Put the ketchup on the heat for 24 minutes with 2 teaspoon")
    assert "200°C" in s and s.endswith(".")
    assert m.tidy_step("take from the fire") == "Take off the heat."
    assert m.tidy_step("add a half-teaspoons of salt") == "Add a half teaspoon of salt."


def test_junk_lines_and_pointers_are_dropped():
    assert all(m.is_junk(x) for x in ["O 002 00.", "DO NOT COOK.", "PAGE Cream Sauce 132 Game Sauce 132 German Sauce 133", "12"])
    assert not m.is_junk("Mix the flour and the water.")
    assert m.tidy_step("Cook for 5 minutes (see Recipe Notes).") == "Cook for 5 minutes."


def test_ingredient_list_step_becomes_ingredients():
    r = rec("Candy", [("", "water")], ["Two cups of brown sugar, one cup of chopped peanuts, butter the size of an egg.", "Boil until thick and pour out."])
    notes, reason = m.process(r, set())
    items = {i["item"]: i["amount"] for i in r["ingredients"]}
    assert "brown sugar" in items and items["brown sugar"].startswith("480 ml") and "chopped peanuts" in items
    assert items["butter"] == "size of an egg"
    assert r["steps"] == ["Boil until thick and pour out."] and reason is None


def test_run_together_ingredient_is_cut_and_missing_ones_added_from_method():
    r = rec("Cookies", [("225 g (1 cup)", "sweet butter and two cups")], ["Beat the butter, then add 3 cups of flour and 1 tablespoon of salt.", "Bake until golden."])
    m.process(r, set())
    items = [i["item"] for i in r["ingredients"]]
    assert "sweet butter" in items and "flour" in items and "salt" in items


def test_recipes_that_point_elsewhere_or_name_a_batch_are_flagged():
    _, reason = m.process(rec("A", [("1", "egg"), ("1", "flour")], ["Prepare 2 recipes Barbecue Sauce, Recipe No. B 025 00.", "Mix."], "https://archive.org/details/x"), set())
    assert reason == "points at another recipe"
    _, reason = m.process(rec("B", [("1", "egg"), ("1", "flour")], ["Shingle 25 steaks into each pan.", "Bake."], "https://archive.org/details/x"), set())
    assert reason == "method names a large-batch size"


def test_short_recipes_pass_only_when_the_list_covers_the_method():
    ok = rec("Taffy", [("75 g", "sugar"), ("60 ml", "water"), ("30 ml", "vinegar")], ["Mix the ingredients and boil 20 minutes, then pour into a buttered pan and pull."])
    assert m.relaxed_ok(ok)
    bad = rec("Sandwich", [("1 tsp", "melted butter"), ("1 drop", "vinegar")], ["Mash the yolks of five hard-boiled eggs with the butter and spread on bread."])
    assert not m.relaxed_ok(bad)


def test_title_cleanup():
    assert m.modern_title("Oyster Catsup") == "Oyster Ketchup"
    assert m.modern_title("Mammy’S Patties") == "Mammy’s Patties"
