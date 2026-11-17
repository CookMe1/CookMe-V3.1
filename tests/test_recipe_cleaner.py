import sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
from recipe_cleaner import clean_steps, clean_amount, clean_ingredient, is_cookable

def test_label_steps_dropped_and_numbers_stripped():
    assert clean_steps(["step 1", "Chop the onion.", "2", "▢", "STEP 3", "Step 4: Fry it.", "5. Serve."]) == ["Chop the onion.", "Fry it.", "Serve."]

def test_short_real_steps_kept():
    assert clean_steps(["Mix well.", "Enjoy!"]) == ["Mix well.", "Enjoy!"]

def test_long_block_split_into_steps():
    block = " ".join(f"Do thing number {i} carefully in the pan." for i in range(20))
    out = clean_steps([block]); assert len(out) > 3 and all(len(s) < 260 for s in out)

def test_amounts():
    assert clean_amount("1.0 cup") == "1 cup" and clean_amount("0.5 teaspoon") == "1/2 teaspoon"
    assert clean_amount("2.0 tablespoons") == "2 tablespoons" and clean_amount("1.5 cups") == "1 1/2 cups"
    assert clean_amount("1/2 tsp") == "1/2 tsp" and clean_amount("100g") == "100g" and clean_amount("350.5g") == "350.5g"

def test_descriptor_amounts_moved_into_name():
    assert clean_ingredient({"item": "Rice", "amount": "White"}) == {"item": "White Rice", "amount": ""}
    assert clean_ingredient({"item": "Onion", "amount": "Chopped"})["item"] == "Onion, chopped"
    assert clean_ingredient({"item": "Salt", "amount": "Pinch"})["amount"] == "Pinch"
    assert clean_ingredient({"item": "Salt", "amount": "To taste"})["amount"] == "To taste"

def test_master_file_is_clean_and_cookable():
    data = json.load(open(ROOT / "data" / "master_recipes.json", encoding="utf-8"))
    assert len(data) > 1000
    for r in data:
        assert is_cookable(r), r["title"]
        assert all(len(s) > 3 and any(c.isalpha() for c in s) for s in r["steps"]), r["title"]
        assert all(not i["amount"].replace(".0 ", " ").endswith(".0") for i in r["ingredients"])
