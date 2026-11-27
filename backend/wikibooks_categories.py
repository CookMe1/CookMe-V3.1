"""Use the categories a Wikibooks page already carries ("Indian recipes", "Halal recipes", "Slow cooker recipes"...) to set
cuisine and tags, instead of guessing from the title. Pure functions, no network."""
import re

CUISINE = {
    "american": "united states|southern u\\.s\\.|southwestern|texas|louisiana|californian|midwestern u\\.s\\.|tex-mex|north american|hawaiian|creole|native american|italian-american",
    "british": "english|scottish|cornish|manx|northern irish|british",
    "irish": "irish",
    "indian": "indian|bengali|punjabi|sindhi|south indian|dal",
    "south_asian": "pakistani|pashtun|sri lankan|nepali|afghan|south asian|bangladeshi",
    "middle_eastern": "middle eastern|palestinian|jordanian|iraqi|israeli|jewish yemenite|egyptian|jewish",
    "turkish": "turkish",
    "moroccan": "moroccan",
    "african": "african|nigerian|national nigerian|yoruba|igbo|efik|hausa|tiv|zambian|gambian|cameroonian|chadian|senegalese|rwandan|ugandan|south african|ghanian|ghanaian|kenyan|tanzanian|cape verdean|liberian|sudanese|somali|algerian|libyan|tunisian|ethiopian",
    "chinese": "chinese|taiwanese|douchi",
    "japanese": "japanese", "korean": "korean", "thai": "thai", "vietnamese": "vietnamese",
    "southeast_asian": "indonesian|malaysian|filipino|cambodian|southeast asian",
    "asian": "asian|east asian|tibetan|mongolian|azerbaijani",
    "mexican": "mexican",
    "caribbean": "caribbean|cuban|puerto rican|dominican",
    "latin_american": "brazilian|peruvian|argentine|colombian|venezuelan|chilean|south american|costa rican",
    "french": "french|alsatian", "german": "german", "italian": "italian", "spanish": "spanish", "greek": "greek|cypriot",
    "mediterranean": "mediterranean|gibraltarian", "polish": "polish", "russian": "russian|ukrainian",
    "european": "european|austrian|albanian|bulgarian|croatian|hungarian|danish|swedish|norwegian|finnish|estonian|lithuanian|dutch|belgian",
}
_CUISINE_RE = [(k, re.compile(rf"^(?:{v})(?: recipes| cuisine)$", re.I)) for k, v in CUISINE.items()]

TAGS = {
    r"^halal recipes$": ["halal"], r"^kosher(?: for passover)? recipes$": ["kosher"], r"^pescatarian recipes$": ["pescatarian"],
    r"^(?:naturally )?gluten-free recipes$": ["gluten-free"], r"^inexpensive recipes$": ["budget", "cheap"],
    r"^slow cooker recipes$": ["slow cooker", "crockpot"], r"^air fried recipes$": ["air fryer"], r"^microwave recipes$": ["microwave"],
    r"^kid-friendly recipes$": ["kid friendly"], r"^camping recipes$": ["camping"], r"^barbecue recipes$": ["bbq"],
    r"^(?:very )?easy recipes$": ["easy"], r"^breakfast recipes$": ["breakfast"], r"^side dish recipes$": ["side dish"],
    r"^appetizer recipes$": ["starter"], r"^snacks? recipes$": ["snack"], r"^christmas recipes$": ["christmas"],
    r"^(?:recipes for )?soup recipes?$|^recipes for soup$": ["soup"], r"^low-gi recipes$": ["low gi"],
    # sections of the app: Drinks, Sauces & Dressings, Snacks
    r"^recipes for (?:alcoholic )?beverages$|^beverages$": ["drink"], r"^recipes for alcoholic beverages$": ["alcoholic"],
    r"^recipes for cocktails$": ["drink", "cocktail", "alcoholic"], r"^recipes for smoothies$": ["drink", "smoothie"],
    r"^recipes for tea and tisanes$|^tea recipes$": ["drink", "tea"], r"^recipes for juice$": ["drink", "juice"],
    r"^recipes for sauces and condiments$|^condiments$|^household cyclopedia sauce recipes$|^recipes for (?:pasta|barbecue|hot|brown|béchamel|marinara) sauce$": ["sauce"],
    r"^recipes for salad dressing$": ["sauce", "dressing"], r"^recipes for dip$": ["sauce", "dip"], r"^marinade recipes$": ["sauce", "marinade"],
    r"^spread recipes$": ["sauce", "spread"], r"^recipes for syrup$|^syrups$": ["sauce", "syrup"], r"^snacks? recipes$": ["snack"],
}

# When a page has no helpful category, fall back on the name (kept strict so a "Chicken Soup" never lands in Drinks)
TITLE_KINDS = [
    ("drink", re.compile(r"smoothie|cocktail|lemonade|\btea\b|coffee|punch|milkshake|\bshake\b|\bjuice\b|cider|mulled|\bwine\b|liqueur|sangria|margarita|martini|latte|hot chocolate|eggnog|\bale\b|\bbeer\b|frappe|spritzer|kombucha|\blassi\b", re.I)),
    ("dressing", re.compile(r"dressing|vinaigrette", re.I)),
    ("sauce", re.compile(r"\bsauce\b|\bdip\b|salsa|marinade|\bgravy\b|chutney|relish|aioli|pesto|mayonnaise|\brub\b|hummus|guacamole|\bglaze\b|\bsyrup\b|ketchup|mustard|pickle", re.I)),
    ("snack", re.compile(r"\bsnack\b|popcorn|\bchips\b|crackers?\b|trail mix|granola bar|energy ball|jerky|nachos", re.I)),
]


def kind_tags(title, tags=()):
    """-> extra tags like ['drink'] or ['sauce','dressing'] from the title, only if the categories did not already say."""
    have = {str(t).lower() for t in tags}
    if have & {"drink", "sauce", "snack"}:
        return []
    for kind, rx in TITLE_KINDS:
        if rx.search(title or ""):
            return ["sauce", "dressing"] if kind == "dressing" else [kind]
    return []


def is_special_kind(tags):
    return bool({str(t).lower() for t in tags} & {"drink", "sauce", "dressing", "dip", "marinade", "snack", "spread", "syrup"})


# Items that never need a quantity ("salt", "oil for frying", "water")
NO_AMOUNT_NEEDED = re.compile(r"^(?:freshly[- ]?ground |ground |black |white |sea |kosher |table |extra[- ]virgin |vegetable |olive |cooking |frying )*"
                              r"(?:salt|pepper|oil|olive oil|water|ice|ice cubes|cooking spray|butter for|garnish|to taste|for serving|for frying|for greasing|for dusting)\b|"
                              r"\b(?:to taste|for (?:serving|frying|greasing|dusting|garnish)|as needed|optional)\b", re.I)
EXCLUDE = re.compile(r"^(?:pet|duplicate) recipes$", re.I)


def from_categories(cats):
    """-> {"cuisine": str, "tags": [..], "dessert": bool, "exclude": bool}"""
    cuisine, tags, dessert, exclude = "", [], False, False
    for c in cats:
        c = c.replace("_", " ").strip()
        if EXCLUDE.match(c):
            exclude = True
        if re.match(r"^recipes for dessert$", c, re.I):
            dessert = True
        for pat, t in TAGS.items():
            if re.match(pat, c, re.I):
                tags += t
        if not cuisine:
            for k, rx in _CUISINE_RE:
                if rx.match(c):
                    cuisine = k
                    break
    return {"cuisine": cuisine, "tags": sorted(set(tags)), "dessert": dessert, "exclude": exclude}
