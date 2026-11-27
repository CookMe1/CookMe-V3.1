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
}
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
