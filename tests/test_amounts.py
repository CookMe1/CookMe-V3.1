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
