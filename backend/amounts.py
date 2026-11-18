"""Turn an ingredient amount ("2 cups", "1 sliced", "6 cloves", "8", "drizzle") into approximate grams.

Used for nutrition. Units are matched as whole words (so the "l" in "sliced" is not litres), counts like
"8" eggs use a typical weight per item, and vague amounts ("pinch", "drizzle") are small, not 100 g.
"""
import re

UNICODE_FRACTIONS = {"½": 0.5, "¼": 0.25, "¾": 0.75, "⅓": 1 / 3, "⅔": 2 / 3, "⅛": 0.125, "⅜": 0.375, "⅝": 0.625}

# grams per unit (volume units use a water-like 1 g/ml; good enough for an estimate)
UNITS = {
    "kg": 1000, "kilo": 1000, "kilos": 1000, "g": 1, "gram": 1, "grams": 1, "gr": 1, "mg": 0.001,
    "l": 1000, "litre": 1000, "litres": 1000, "liter": 1000, "liters": 1000, "ml": 1, "cl": 10, "dl": 100,
    "cup": 240, "cups": 240, "tbsp": 15, "tbs": 15, "tablespoon": 15, "tablespoons": 15,
    "tsp": 5, "teaspoon": 5, "teaspoons": 5, "fl oz": 30, "floz": 30,
    "oz": 28, "ounce": 28, "ounces": 28, "lb": 454, "lbs": 454, "pound": 454, "pounds": 454,
    "clove": 4, "cloves": 4, "slice": 30, "slices": 30, "piece": 100, "pieces": 100,
    "can": 400, "cans": 400, "tin": 400, "tins": 400, "handful": 30, "handfuls": 30,
    "bunch": 60, "bunches": 60, "sprig": 2, "sprigs": 2, "stick": 110, "sticks": 110,
    "pinch": 0.4, "pinches": 0.4, "dash": 0.6, "splash": 10, "drizzle": 7, "knob": 15, "glug": 15,
    "pack": 250, "packet": 250, "packets": 250, "jar": 300, "stalk": 40, "stalks": 40, "head": 500,
    "fillet": 150, "fillets": 150, "rasher": 25, "rashers": 25, "leaf": 1, "leaves": 1,
}
VAGUE = ("to taste", "to serve", "for serving", "for garnish", "as needed", "some", "a little", "optional")

# typical weight of one whole item, matched against the ingredient name
COUNT_WEIGHTS = [
    ("egg", 50), ("onion", 110), ("shallot", 40), ("spring onion", 15), ("garlic", 4), ("tomato", 120),
    ("potato", 170), ("sweet potato", 200), ("carrot", 70), ("lemon", 60), ("lime", 45), ("orange", 150),
    ("apple", 180), ("banana", 120), ("pear", 170), ("avocado", 150), ("pepper", 150), ("chilli", 15),
    ("chili", 15), ("jalapeno", 15), ("jalapeño", 15), ("courgette", 200), ("zucchini", 200),
    ("aubergine", 250), ("eggplant", 250), ("cucumber", 300), ("celery", 40), ("leek", 150),
    ("baguette", 250), ("bread", 30), ("roll", 60), ("bun", 60), ("tortilla", 40), ("pitta", 60),
    ("chicken breast", 170), ("chicken thigh", 120), ("sausage", 60), ("bacon", 25), ("burger", 120),
    ("steak", 200), ("chop", 150), ("fillet", 150), ("mushroom", 20), ("beetroot", 80), ("turnip", 120),
    ("peach", 150), ("plum", 60), ("mango", 200), ("kiwi", 75), ("date", 8), ("fig", 50),
    ("star anise", 1), ("bay leaf", 0.5), ("bay leaves", 0.5), ("cinnamon stick", 3), ("cardamom", 0.5),
    ("clove", 1), ("tomato", 120), ("cabbage", 600), ("cauliflower", 600), ("broccoli", 300),
]
DEFAULT_COUNT_G = 80


def _number(text: str):
    """First quantity in text: handles 1 1/2, 3/4, 0.5, 2-3 (average), unicode fractions. Returns (value, end_index)."""
    for f, v in UNICODE_FRACTIONS.items():
        text = re.sub(rf"(\d)\s*{f}", lambda m, v=v: str(int(m.group(1)) + v), text)
        text = text.replace(f, str(v))
    m = re.search(r"(\d+(?:\.\d+)?)\s+(\d+)\s*/\s*(\d+)", text)           # 1 1/2
    if m:
        return float(m.group(1)) + int(m.group(2)) / int(m.group(3)), text, m.end()
    m = re.search(r"(\d+)\s*/\s*(\d+)", text)                              # 3/4
    if m:
        return int(m.group(1)) / int(m.group(2)), text, m.end()
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:-|–|to)\s*(\d+(?:\.\d+)?)", text)  # 2-3
    if m:
        return (float(m.group(1)) + float(m.group(2))) / 2, text, m.end()
    m = re.search(r"\d+(?:\.\d+)?", text)
    if m:
        return float(m.group()), text, m.end()
    return None, text, 0


def _count_weight(item_name: str) -> float:
    name = (item_name or "").lower()
    best = None
    for key, grams in COUNT_WEIGHTS:               # longest matching key wins ("sweet potato" over "potato")
        if re.search(rf"\b{re.escape(key)}s?\b", name) and (best is None or len(key) > len(best[0])):
            best = (key, grams)
    return best[1] if best else DEFAULT_COUNT_G


def parse_amount_to_grams(amount: str, item_name: str = "") -> float:
    text = (amount or "").strip().lower()
    if not text:
        return 5.0                                   # no amount given: a seasoning-sized default, not 100 g
    pack = re.search(r"(\d+(?:\.\d+)?)\s*x?\s*\(?\s*(\d+(?:\.\d+)?)\s*(g|ml|oz)\b", text)   # "2 x 400g", "1 (400g) can"
    if pack and re.search(r"\(|x", text):
        n, size, u = float(pack.group(1)), float(pack.group(2)), pack.group(3)
        return n * size * (28 if u == "oz" else 1)
    qty, text, end = _number(text)
    words = re.findall(r"[a-z]+(?:\s?oz)?", text[end:] if qty is not None else text)
    unit_g = None
    for w in ([text[end:].strip().split(" ")[0]] if qty is not None else []) + words:
        w = re.sub(r"[^a-z]", "", w)
        if w in UNITS:
            unit_g = UNITS[w]
            break
    if qty is None:                                   # "pinch", "drizzle", "handful", "to taste"
        return unit_g if unit_g is not None else 5.0
    if unit_g is not None:
        return qty * unit_g
    if any(v in text for v in VAGUE):
        return 5.0
    # no unit: either grams written bare ("400") or a count of items ("8" eggs, "1 sliced" onion)
    if qty >= 25:
        return qty
    return qty * _count_weight(item_name)
