import pytest
from amounts import parse_amount_to_grams as g


@pytest.mark.parametrize("amount,item,expected", [
    ("1 sliced", "Onion", 110), ("6 cloves", "Garlic", 24), ("8", "Eggs", 400), ("1", "Baguette", 250),
    ("400g", "Potatoes", 400), ("1kg", "Beef", 1000), ("4 tbsp", "Olive Oil", 60), ("1 1/2 cups", "Flour", 360),
    ("½ tsp", "Salt", 2.5), ("250ml", "Milk", 250), ("2 oz", "Cheese", 56), ("400", "Rice", 400),
    ("1 (400g) can", "Tomatoes", 400), ("2 x 400g", "Tomatoes", 800),
])
def test_amounts(amount, item, expected):
    assert g(amount, item) == pytest.approx(expected, rel=0.01)


def test_vague_amounts_are_small():
    assert g("pinch", "Salt") < 1 and g("drizzle", "Olive oil") < 10 and g("", "Salt") <= 5 and g("to taste", "Pepper") <= 5


def test_range_uses_average_and_unit_words_need_whole_match():
    assert g("2-3", "Carrots") == pytest.approx(175)
    assert g("1 large", "Onion") == 110       # "l" in "large" is not litres


def test_servings_and_bare_seasonings_are_small():
    from amounts import parse_amount_to_grams as g
    assert g("4 servings", "salt") == 4          # was 320 g
    assert g("4 servings", "korean marinade") == 120
    assert g("2", "salt") == 2
    assert g("2", "onion") == 220                # real counts are unchanged


def test_cups_of_dry_goods_and_cooked_rice():
    from amounts import adjust_cups
    assert adjust_cups("1 cup", "plain flour", 240, 4) == (125, 1.0)
    assert adjust_cups("1 cup", "basmati rice", 240, 4) == (185, 1.0)          # 1/4 cup each: raw
    g, f = adjust_cups("6 cups", "rice", 1440, 4)                                # 1.5 cups each: cooked
    assert round(g) == 948 and f == 0.36
    assert adjust_cups("2 cups", "cooked rice", 480, 4) == (480, 1.0)
    assert adjust_cups("2 tbsp", "rice vinegar", 30, 4) == (30, 1.0)


def test_split_ingredient():
    from amounts import split_ingredient as sp
    assert sp("2 tablespoons olive oil") == ("2 tablespoons", "olive oil")
    assert sp("1 large yellow onion, chopped") == ("1", "large yellow onion, chopped")
    assert sp("1 1/2 cups chicken broth") == ("1 1/2 cups", "chicken broth")
    assert sp("1 (15-ounce) can white beans, drained") == ("1 (15-ounce) can", "white beans, drained")
    assert sp("Salt and pepper") == ("", "Salt and pepper")
    assert sp("½ teaspoon cumin") == ("½ teaspoon", "cumin")


def test_library_style_ingredients():
    from amounts import parse_amount_to_grams as g, fry_factor
    assert g("1", "Red Pepper") == 150                      # a vegetable, not a seasoning
    assert g("1", "Black Pepper") == 1
    assert g("2 tblsp", "Red Wine Vinegar") == 30
    assert g("10", "Almonds") == 12
    assert g("1 cup", "salt") == 30                         # capped
    assert g("1 Handfull", "Pork") == 30
    assert fry_factor("Sunflower Oil", 1000, 4) == 0.12
    assert fry_factor("Olive Oil", 30, 4) == 1.0
