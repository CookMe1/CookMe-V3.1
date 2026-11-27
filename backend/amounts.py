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
    "cup": 240, "cups": 240, "tbsp": 15, "tbs": 15, "tblsp": 15, "tbl": 15, "tbls": 15, "tbsps": 15, "tblsps": 15, "dsp": 10, "tsps": 5, "tablespoon": 15, "tablespoons": 15,
    "tsp": 5, "teaspoon": 5, "teaspoons": 5, "fl oz": 30, "floz": 30,
    "oz": 28, "ounce": 28, "ounces": 28, "lb": 454, "lbs": 454, "pound": 454, "pounds": 454,
    "clove": 4, "cloves": 4, "slice": 30, "slices": 30, "piece": 100, "pieces": 100,
    "can": 400, "cans": 400, "tin": 400, "tins": 400, "handful": 30, "handfuls": 30, "handfull": 30,
    "bunch": 60, "bunches": 60, "sprig": 2, "sprigs": 2, "stick": 110, "sticks": 110,
    "pinch": 0.4, "pinches": 0.4, "dash": 0.6, "splash": 10, "drizzle": 7, "knob": 15, "glug": 15,
    "pack": 250, "packet": 250, "packets": 250, "jar": 300, "stalk": 40, "stalks": 40, "head": 500,
    "fillet": 150, "fillets": 150, "rasher": 25, "rashers": 25, "leaf": 1, "leaves": 1,
    "part": 30, "parts": 30, "shot": 44, "shots": 44, "jigger": 44, "jiggers": 44, "measure": 25, "measures": 25, "dashes": 0.6,
    "drop": 0.05, "drops": 0.05, "scoop": 65, "scoops": 65, "glass": 250, "pint": 473, "bottle": 330, "mililiter": 1, "mililiters": 1,
    "serving": 30, "servings": 30, "portion": 30, "portions": 30,      # "4 servings" of a sauce: about a spoonful each
}
SERVING_WORDS = {"serving", "servings", "portion", "portions"}
# seasonings are tiny: "4 servings salt" is about 4 g, not 4 whole items
SEASONING = re.compile(r"\b(salt|sazon|adobo|bouillon|(?:^|(?<=black )|(?<=white )|(?<=ground )|(?<=cracked )|(?<=cayenne ))pepper|paprika|cumin|oregano|thyme|basil|parsley|cinnamon|nutmeg|turmeric|"
                       r"coriander|chilli powder|chili powder|garlic powder|onion powder|spice|spices|seasoning|herbs?)\b")
VAGUE = ("to taste", "to serve", "for serving", "for garnish", "as needed", "some", "a little", "optional")

# typical weight of one whole item, matched against the ingredient name
COUNT_WEIGHTS = [
    ("egg", 50), ("onion", 110), ("shallot", 40), ("spring onion", 15), ("garlic", 4), ("tomato", 120),
    ("potato", 170), ("sweet potato", 200), ("carrot", 70), ("lemon", 60), ("lime", 45), ("orange", 150),
    ("apple", 180), ("banana", 120), ("pear", 170), ("avocado", 150), ("pepper", 150), ("grape", 5), ("strawberry", 15), ("strawberries", 15), ("almonds", 1.2), ("hazelnuts", 1.5), ("prawn", 15), ("shrimp", 15), ("meatball", 30), ("cherry tomato", 15), ("sage leaf", 0.5), ("chilli", 15),
    ("chili", 15), ("jalapeno", 15), ("jalapeño", 15), ("courgette", 200), ("zucchini", 200),
    ("aubergine", 250), ("eggplant", 250), ("cucumber", 300), ("celery", 40), ("leek", 150),
    ("baguette", 250), ("bread", 30), ("roll", 60), ("bun", 60), ("tortilla", 40), ("pitta", 60),
    ("chicken breast", 170), ("chicken thigh", 120), ("sausage", 60), ("bacon", 25), ("burger", 120),
    ("steak", 200), ("chop", 150), ("fillet", 150), ("mushroom", 20), ("beetroot", 80), ("turnip", 120),
    ("almond", 1.2), ("hazelnut", 1.5), ("walnut", 4), ("cashew", 1.5), ("pecan", 3), ("olive", 4), ("peach", 150), ("plum", 60), ("mango", 200), ("kiwi", 75), ("date", 8), ("fig", 50),
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
    # "2 x 400g", "1 (400g) can", "1 packet (7 g)": a count followed by the size of each. The number must start at a number
    # boundary, so "500 g (4 cups)" is never read as "5 x 00 g".
    pack = re.search(r"(?<![\d./])(\d+(?:\.\d+)?)\s*(?:x\s*\(?|\(|(?:cans?|tins?|jars?|packets?|packs?|packages?|bottles?|cartons?|bags?|boxes|box|sachets?|tubs?|blocks?|sticks?)\s*\()\s*(\d+(?:\.\d+)?)\s*(g|ml|oz)\b", text)
    if pack and not re.match(r"\s*\d+(?:\.\d+)?\s*(?:g|ml|oz|kg|l)\b", text):
        n, size, u = float(pack.group(1)), float(pack.group(2)), pack.group(3)
        return n * size * (28 if u == "oz" else 1)
    # "2 cups (300 g)", "16 Tbsp (8 oz / 227 g)": when a weight in grams is given in brackets, trust it over the cup/spoon guess
    paren = re.search(r"\([^)]*?(\d+(?:\.\d+)?)\s*(kg|g)\b[^)]*\)", text)
    if paren and not re.match(r"\s*\d+(?:\.\d+)?\s*(?:g|kg)\b", text):
        return float(paren.group(1)) * (1000 if paren.group(2) == "kg" else 1)
    bare = re.sub(r"\s*\([^)]*\)", "", text).strip()          # "1 kg (2 1/2 lbs)" -> "1 kg": the bracket repeats the amount in other units
    if re.search(r"[\d¼½¾⅐-⅞]", bare):
        text = bare
    qty, text, end = _number(text)
    words = re.findall(r"[a-z]+(?:\s?oz)?", text[end:] if qty is not None else text)
    unit_g = None
    for w in ([text[end:].strip().split(" ")[0]] if qty is not None else []) + words:
        w = re.sub(r"[^a-z]", "", w)
        if w in UNITS:
            unit_g = UNITS[w]
            if w in SERVING_WORDS and SEASONING.search((item_name or "").lower()):
                unit_g = 1
            break
    if qty is None:                                   # "pinch", "drizzle", "handful", "to taste"
        return unit_g if unit_g is not None else 5.0
    if unit_g is not None:
        grams = qty * unit_g
        if SEASONING.search((item_name or "").lower()):
            grams = min(grams, 30.0)                 # no recipe uses a cup of salt
        return grams
    if any(v in text for v in VAGUE):
        return 5.0
    # no unit: either grams written bare ("400") or a count of items ("8" eggs, "1 sliced" onion)
    if qty >= 25:
        return qty
    if SEASONING.search((item_name or "").lower()):      # "2 salt" or "3 pepper": a few grams, never 80 g each
        return qty * 1.0
    return qty * _count_weight(item_name)


# A cup of dry goods weighs much less than a cup of water (the default above): grams per cup
CUP_GRAMS = [("rice", 185), ("quinoa", 170), ("couscous", 175), ("oats", 90), ("flour", 125),
             ("sugar", 200), ("pasta", 100), ("lentil", 190), ("breadcrumb", 110)]
COOKED_GRAINS = ("rice", "quinoa", "couscous")
COOKED_CUP_G = 158          # a cup of cooked rice
COOKED_FACTOR = 0.36        # cooked rice carries about 36% of the calories of the same weight of raw rice


def adjust_cups(amount: str, item_name: str, grams: float, servings: int):
    """Better weight for cups of dry goods, and a cooked-rice correction.

    "6 cups rice" for 4 servings is cooked rice (1.5 cups raw per person would be a huge portion), so it is
    weighed as cooked and its raw nutrition values are scaled down. Returns (grams, nutrition_factor)."""
    text = (amount or "").lower()
    name = (item_name or "").lower()
    if re.search(r"\d\s*(?:kg|kilo(?:gram)?s?|grams?|g|oz|ounces?|lbs?|pounds?|ml|millilit\w+|lit(?:er|re)s?|l)\b", text):          # a weight or volume is written out ("500 g (4 cups)"): trust it
        return grams, 1.0
    if not re.search(r"\bcups?\b", text) or re.search(r"\bcooked\b", name + " " + text):
        return grams, 1.0
    qty, _, _ = _number(text)
    if not qty:
        return grams, 1.0
    for key, per_cup in CUP_GRAMS:
        if re.search(rf"\b{key}s?\b", name):
            if key in COOKED_GRAINS and qty / max(1, servings) > 0.75:
                return qty * COOKED_CUP_G, COOKED_FACTOR
            return qty * per_cup, 1.0
    return grams, 1.0


_QTY = r"(?:\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?(?:\s*(?:-|to)\s*\d+(?:\.\d+)?)?|[½¼¾⅓⅔⅛])"
_SPLIT = re.compile(
    rf"^\s*(?P<q>{_QTY}(?:\s*[½¼¾⅓⅔⅛])?)\s*(?P<u>(?:\([^)]*\)\s*)?(?:[a-zA-Z]+\.?)?)\s+(?P<rest>.+)$")


def split_ingredient(line: str):
    """"2 tablespoons olive oil" -> ("2 tablespoons", "olive oil"); "1 large onion, chopped" -> ("1", "large onion, chopped")."""
    m = _SPLIT.match(line or "")
    if not m:
        return "", (line or "").strip()
    unit = (m.group("u") or "").strip()
    rest = m.group("rest").strip()
    if unit and unit.lower().rstrip(".") not in {u for u in UNITS} | {"oz", "ounce", "can", "cans"} and not unit.startswith("("):
        rest = f"{unit} {rest}"                    # the word was part of the name ("1 large onion")
        unit = ""
    return f"{m.group('q').strip()} {unit}".strip(), rest


OILS = re.compile(r"\b(oil|lard|dripping|frying fat|ghee)\b")


def fry_factor(item_name: str, grams: float, servings: int) -> float:
    """Oil for deep frying is mostly left in the pan: above ~40 g per serving, count only a share of it."""
    if OILS.search((item_name or "").lower()) and grams / max(1, servings) > 40:
        return 0.12
    return 1.0
