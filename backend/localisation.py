"""
localisation.py
===============
All per-country/language personalisation data in one place.

Features:
  1. Ingredient synonyms    — courgette ↔ zucchini, cilantro ↔ coriander etc.
  2. Measurement system     — metric (g/ml) vs imperial (oz/cups) by language
  3. Dietary defaults       — sensible regional dietary filter defaults
  4. Currency symbols       — £/€/$/₹/¥ by language
  5. Seasonal calendar      — in-season produce by hemisphere + month

All data is static — zero API calls, zero AI cost.
"""

from datetime import datetime
from typing import Optional


# ═══════════════════════════════════════════════════════════════════════════════
# 1. INGREDIENT SYNONYMS
# Maps every regional name to a canonical English key.
# Used to normalise ingredient names before pantry matching so
# "calabacín" and "courgette" both match a recipe calling for "zucchini".
# ═══════════════════════════════════════════════════════════════════════════════

# canonical_name → [all regional synonyms, all lower-cased]
INGREDIENT_SYNONYMS: dict[str, list[str]] = {
    "zucchini": [
        "courgette", "courgettes", "zucchini", "zucchinis",
        "calabacín", "calabacin", "zucchetto", "courge",
        "zucchino", "curgete",
    ],
    "eggplant": [
        "aubergine", "aubergines", "eggplant", "eggplants",
        "berenjena", "berenjenas", "melanzana", "melanzane",
        "aubergine violette", "brinjal",
    ],
    "cilantro": [
        "coriander", "fresh coriander", "cilantro", "cilantro leaves",
        "dhania", "kothimbir", "cotija", "coriandre",
        "koriander", "culantro",
    ],
    "ground beef": [
        "mince", "beef mince", "minced beef", "ground beef",
        "carne picada", "carne molida", "viande hachée", "hackfleisch",
        "gehakt", "macinato di manzo",
    ],
    "shrimp": [
        "prawns", "prawn", "shrimp", "shrimps",
        "gambas", "crevettes", "garnelen", "gamberi",
        "camarón", "camarones",
    ],
    "cookies": [
        "biscuits", "cookies", "cookie", "galletas", "biscotti",
        "kekse", "biscoitos", "biscuits secs",
    ],
    "superfine sugar": [
        "caster sugar", "castor sugar", "superfine sugar",
        "azúcar glass", "azúcar superfino", "sucre semoule",
        "feiner zucker", "zucchero a velo",
    ],
    "confectioners sugar": [
        "icing sugar", "powdered sugar", "confectioners sugar",
        "azúcar impalpable", "sucre glace", "puderzucker",
        "zucchero a velo", "açúcar de confeiteiro",
    ],
    "heavy cream": [
        "double cream", "heavy cream", "whipping cream",
        "crème fraîche épaisse", "nata para montar", "panna da cucina",
        "sahne", "natas", "crème double",
    ],
    "sour cream": [
        "sour cream", "soured cream", "crème fraîche",
        "crema agria", "crème aigre", "saure sahne",
        "panna acida", "creme azedo",
    ],
    "scallion": [
        "spring onion", "spring onions", "scallion", "scallions",
        "green onion", "green onions", "cebolleta", "cebollín",
        "oignon nouveau", "frühlingszwiebel", "cipollotto",
    ],
    "bell pepper": [
        "capsicum", "bell pepper", "bell peppers", "sweet pepper",
        "pimiento", "poivron", "paprika", "peperone",
        "paprike", "páprica",
    ],
    "cornstarch": [
        "cornflour", "cornstarch", "corn starch",
        "maizena", "fécule de maïs", "maïzena",
        "amido di mais", "maisena",
    ],
    "all-purpose flour": [
        "plain flour", "all-purpose flour", "all purpose flour",
        "harina de trigo", "farine de blé", "mehl",
        "farina 00", "farinha de trigo",
    ],
    "whole milk": [
        "full fat milk", "whole milk", "full cream milk",
        "leche entera", "lait entier", "vollmilch",
        "latte intero", "leite integral",
    ],
    "beet": [
        "beetroot", "beet", "beets",
        "remolacha", "betterave", "rote bete",
        "barbabietola", "beterraba",
    ],
    "arugula": [
        "rocket", "arugula", "rucola", "rúcula",
        "roquette", "rucola selvatica",
    ],
    "chickpeas": [
        "chickpeas", "chick peas", "garbanzo beans", "garbanzos",
        "pois chiches", "kichererbsen", "ceci",
        "grão de bico", "garbanzos",
    ],
    "ground pork": [
        "pork mince", "minced pork", "ground pork",
        "carne de cerdo picada", "porc haché", "hackfleisch schwein",
    ],
    "bacon": [
        "bacon", "streaky bacon", "pancetta", "lardons",
        "tocino", "lard fumé", "speck",
    ],
}

# Build reverse lookup: any synonym → canonical name
_SYNONYM_REVERSE: dict[str, str] = {}
for canonical, synonyms in INGREDIENT_SYNONYMS.items():
    for syn in synonyms:
        _SYNONYM_REVERSE[syn.lower()] = canonical
    _SYNONYM_REVERSE[canonical.lower()] = canonical


def normalise_ingredient(name: str) -> str:
    """
    Resolve a regional ingredient name to its canonical English equivalent.
    Returns the canonical name if found, otherwise the original name.

    Examples:
      "courgette"  → "zucchini"
      "coriander"  → "cilantro"
      "beef mince" → "ground beef"
      "chicken"    → "chicken"  (no change — not in synonym map)
    """
    key = name.lower().strip()
    return _SYNONYM_REVERSE.get(key, name.strip())


# ═══════════════════════════════════════════════════════════════════════════════
# 2. MEASUREMENT SYSTEM BY LANGUAGE
# ═══════════════════════════════════════════════════════════════════════════════

# metric: grams, ml, kg, litres (most of the world)
# imperial: cups, tbsp, oz, lbs (US-influenced)
# uk: mix — weight in grams but still uses cups/tbsp in recipes

MEASUREMENT_SYSTEM: dict[str, str] = {
    "en": "uk",       # British English — metric weight, some cup measures
    "es": "metric",   # Spain/Latin America
    "fr": "metric",
    "de": "metric",
    "it": "metric",
    "pt": "metric",
    "nl": "metric",
    "pl": "metric",
    "ru": "metric",
    "zh": "metric",
    "ja": "metric",
    "ko": "metric",
    "ar": "metric",
    "hi": "metric",
    "tr": "metric",
    "sv": "metric",
    "da": "metric",
    "no": "metric",
    "fi": "metric",
    "el": "metric",
    "he": "metric",
    "th": "metric",
    "vi": "metric",
    "id": "metric",
    "ro": "metric",
    "uk_lang": "metric",   # Ukrainian
    "cs": "metric",
    "hu": "metric",
    "ca": "metric",
}

# Unit display labels per system
UNIT_LABELS: dict[str, dict[str, str]] = {
    "metric": {
        "weight_small": "g",
        "weight_large": "kg",
        "volume_small": "ml",
        "volume_large": "l",
        "temp": "°C",
        "temp_unit": "celsius",
    },
    "imperial": {
        "weight_small": "oz",
        "weight_large": "lb",
        "volume_small": "fl oz",
        "volume_large": "cups",
        "temp": "°F",
        "temp_unit": "fahrenheit",
    },
    "uk": {
        "weight_small": "g",
        "weight_large": "kg",
        "volume_small": "ml",
        "volume_large": "l",
        "temp": "°C",
        "temp_unit": "celsius",
    },
}


def get_measurement_system(language_code: str) -> str:
    return MEASUREMENT_SYSTEM.get(language_code, "metric")


def get_unit_labels(language_code: str) -> dict:
    system = get_measurement_system(language_code)
    return UNIT_LABELS.get(system, UNIT_LABELS["metric"])


# ═══════════════════════════════════════════════════════════════════════════════
# 3. DIETARY DEFAULTS BY LANGUAGE/REGION
# These are DEFAULT suggestions shown to users, not hard restrictions.
# Users can always turn them off.
# ═══════════════════════════════════════════════════════════════════════════════

DIETARY_DEFAULTS: dict[str, dict] = {
    "ar": {
        "suggest_halal_filter": True,
        "hide_pork_by_default": True,
        "note": "Halal filter suggested for Arabic-speaking users",
    },
    "tr": {
        "suggest_halal_filter": True,
        "hide_pork_by_default": True,
        "note": "Halal filter suggested for Turkish users",
    },
    "hi": {
        "suggest_vegetarian_filter": True,
        "note": "Vegetarian filter suggested for Hindi-speaking users",
    },
    "he": {
        "suggest_kosher_filter": True,
        "note": "Kosher filter suggested for Hebrew-speaking users",
    },
    "id": {
        "suggest_halal_filter": True,
        "hide_pork_by_default": True,
        "note": "Halal filter suggested for Indonesian users",
    },
}

DEFAULT_DIETARY = {
    "suggest_halal_filter": False,
    "suggest_vegetarian_filter": False,
    "suggest_kosher_filter": False,
    "hide_pork_by_default": False,
}


def get_dietary_defaults(language_code: str) -> dict:
    return {**DEFAULT_DIETARY, **DIETARY_DEFAULTS.get(language_code, {})}


# ═══════════════════════════════════════════════════════════════════════════════
# 4. CURRENCY BY LANGUAGE
# ═══════════════════════════════════════════════════════════════════════════════

CURRENCY: dict[str, dict] = {
    "en":      {"symbol": "£", "code": "GBP", "name": "British Pound"},
    "es":      {"symbol": "€", "code": "EUR", "name": "Euro"},
    "fr":      {"symbol": "€", "code": "EUR", "name": "Euro"},
    "de":      {"symbol": "€", "code": "EUR", "name": "Euro"},
    "it":      {"symbol": "€", "code": "EUR", "name": "Euro"},
    "pt":      {"symbol": "€", "code": "EUR", "name": "Euro"},
    "nl":      {"symbol": "€", "code": "EUR", "name": "Euro"},
    "pl":      {"symbol": "zł", "code": "PLN", "name": "Polish Złoty"},
    "ru":      {"symbol": "₽", "code": "RUB", "name": "Russian Ruble"},
    "zh":      {"symbol": "¥", "code": "CNY", "name": "Chinese Yuan"},
    "ja":      {"symbol": "¥", "code": "JPY", "name": "Japanese Yen"},
    "ko":      {"symbol": "₩", "code": "KRW", "name": "Korean Won"},
    "ar":      {"symbol": "﷼", "code": "SAR", "name": "Saudi Riyal"},
    "hi":      {"symbol": "₹", "code": "INR", "name": "Indian Rupee"},
    "tr":      {"symbol": "₺", "code": "TRY", "name": "Turkish Lira"},
    "sv":      {"symbol": "kr", "code": "SEK", "name": "Swedish Krona"},
    "da":      {"symbol": "kr", "code": "DKK", "name": "Danish Krone"},
    "no":      {"symbol": "kr", "code": "NOK", "name": "Norwegian Krone"},
    "fi":      {"symbol": "€", "code": "EUR", "name": "Euro"},
    "el":      {"symbol": "€", "code": "EUR", "name": "Euro"},
    "he":      {"symbol": "₪", "code": "ILS", "name": "Israeli Shekel"},
    "th":      {"symbol": "฿", "code": "THB", "name": "Thai Baht"},
    "vi":      {"symbol": "₫", "code": "VND", "name": "Vietnamese Dong"},
    "id":      {"symbol": "Rp", "code": "IDR", "name": "Indonesian Rupiah"},
    "ro":      {"symbol": "lei", "code": "RON", "name": "Romanian Leu"},
    "uk":      {"symbol": "₴", "code": "UAH", "name": "Ukrainian Hryvnia"},
    "cs":      {"symbol": "Kč", "code": "CZK", "name": "Czech Koruna"},
    "hu":      {"symbol": "Ft", "code": "HUF", "name": "Hungarian Forint"},
    "ca":      {"symbol": "€", "code": "EUR", "name": "Euro"},
}


def get_currency(language_code: str) -> dict:
    return CURRENCY.get(language_code, {"symbol": "€", "code": "EUR", "name": "Euro"})


# ═══════════════════════════════════════════════════════════════════════════════
# 5. SEASONAL CALENDAR
# Two hemispheres (Northern / Southern) × 12 months.
# Data sourced from UK/EU seasonal produce guides (Northern) and
# Australian/South American guides (Southern).
# ═══════════════════════════════════════════════════════════════════════════════

# Languages/regions in the Southern hemisphere
SOUTHERN_HEMISPHERE_LANGS = {"pt"}   # Brazil primarily; AU/NZ English handled by timezone

# Which languages are in which hemisphere
# Northern hemisphere: most of the world (EU, Asia, Americas north of equator)
# Southern hemisphere: Brazil (pt), Indonesia (id) straddles equator
SOUTHERN_HEMISPHERE_COUNTRIES = {
    "australia", "new zealand", "argentina", "brazil",
    "chile", "south africa", "peru", "uruguay",
}

# Month → in-season produce (Northern Hemisphere, UK/EU focus)
SEASONAL_NORTHERN: dict[int, list[str]] = {
    1:  ["leeks", "parsnips", "swede", "brussels sprouts", "kale", "cabbage",
         "cauliflower", "celeriac", "chicory", "forced rhubarb", "jerusalem artichokes",
         "onions", "potatoes", "turnips", "blood oranges", "clementines"],
    2:  ["leeks", "parsnips", "purple sprouting broccoli", "kale", "cabbage",
         "celeriac", "chicory", "forced rhubarb", "jerusalem artichokes",
         "onions", "savoy cabbage", "swede", "blood oranges", "clementines"],
    3:  ["purple sprouting broccoli", "kale", "leeks", "cabbage", "cauliflower",
         "chicory", "forced rhubarb", "jersey royals", "morel mushrooms",
         "onions", "parsnips", "spring onions"],
    4:  ["asparagus", "jersey royals", "purple sprouting broccoli", "radishes",
         "rhubarb", "spinach", "spring onions", "watercress", "wild garlic",
         "morel mushrooms", "sorrel"],
    5:  ["asparagus", "broad beans", "jersey royals", "lettuce", "peas",
         "radishes", "rhubarb", "rocket", "sorrel", "spinach", "spring onions",
         "watercress", "wild garlic"],
    6:  ["asparagus", "broad beans", "courgettes", "cucumber", "elderflower",
         "gooseberries", "jersey royals", "lettuce", "peas", "radishes",
         "rocket", "strawberries", "summer squash", "tomatoes"],
    7:  ["aubergine", "beetroot", "blackberries", "blackcurrants", "blueberries",
         "broad beans", "cherries", "courgettes", "cucumber", "fennel",
         "french beans", "garlic", "lettuce", "peas", "peppers", "radishes",
         "raspberries", "redcurrants", "rocket", "runner beans", "strawberries",
         "sweetcorn", "tomatoes"],
    8:  ["aubergine", "beetroot", "blackberries", "blueberries", "courgettes",
         "cucumber", "fennel", "french beans", "garlic", "kohlrabi", "leeks",
         "lettuce", "marrow", "onions", "peas", "peppers", "plums",
         "raspberries", "runner beans", "sweetcorn", "tomatoes"],
    9:  ["apples", "aubergine", "beetroot", "blackberries", "butternut squash",
         "courgettes", "cucumber", "damsons", "figs", "garlic", "kohlrabi",
         "leeks", "lettuce", "marrow", "onions", "pears", "peppers",
         "plums", "pumpkin", "runner beans", "sweetcorn", "tomatoes"],
    10: ["apples", "beetroot", "butternut squash", "celery", "chestnuts",
         "courgettes", "fennel", "garlic", "kale", "leeks", "marrow",
         "onions", "parsnips", "pears", "pumpkin", "quince", "swede",
         "sweet potato", "turnips", "wild mushrooms"],
    11: ["beetroot", "brussels sprouts", "celeriac", "celery", "chestnuts",
         "chicory", "jerusalem artichokes", "kale", "leeks", "parsnips",
         "pears", "pumpkin", "quince", "red cabbage", "swede", "turnips",
         "wild mushrooms"],
    12: ["brussels sprouts", "celeriac", "celery", "chestnuts", "chicory",
         "jerusalem artichokes", "kale", "leeks", "parsnips", "pears",
         "red cabbage", "swede", "turnips", "clementines", "cranberries",
         "forced rhubarb"],
}

# Southern hemisphere is ~6 months offset from Northern
def _southern_month(month: int) -> int:
    """Flip hemisphere: month 1 → month 7, month 7 → month 1."""
    return ((month + 5) % 12) + 1

SEASONAL_SOUTHERN: dict[int, list[str]] = {
    m: SEASONAL_NORTHERN[_southern_month(m)]
    for m in range(1, 13)
}


def get_seasonal_produce(
    language_code: str,
    month: Optional[int] = None,
    hemisphere: Optional[str] = None,
) -> list[str]:
    """
    Return list of in-season produce for the given language and month.

    Args:
        language_code: ISO 639-1 code
        month: 1–12, defaults to current month
        hemisphere: "north" | "south" | None (auto-detect from language)
    """
    if month is None:
        month = datetime.now().month

    if hemisphere is None:
        hemisphere = "south" if language_code in SOUTHERN_HEMISPHERE_LANGS else "north"

    calendar = SEASONAL_SOUTHERN if hemisphere == "south" else SEASONAL_NORTHERN
    return calendar.get(month, [])


def is_in_season(
    ingredient: str,
    language_code: str,
    month: Optional[int] = None,
) -> bool:
    """Check if a specific ingredient is currently in season."""
    seasonal = get_seasonal_produce(language_code, month)
    ingredient_lower = ingredient.lower().strip()
    return any(
        ingredient_lower in s or s in ingredient_lower
        for s in seasonal
    )


def get_seasonal_tip(
    ingredient: str,
    language_code: str,
    month: Optional[int] = None,
) -> Optional[str]:
    """
    Return a tip if an ingredient is out of season.
    Returns None if in season (no tip needed).
    """
    if is_in_season(ingredient, language_code, month):
        return None
    seasonal = get_seasonal_produce(language_code, month)
    return (
        f"{ingredient.capitalize()} is not in season this month. "
        f"In-season alternatives: {', '.join(seasonal[:4])}."
    ) if seasonal else None


# ═══════════════════════════════════════════════════════════════════════════════
# 6. REGIONAL CUISINE PREFERENCES
# Used to re-rank community recipes for users based on their language.
# ═══════════════════════════════════════════════════════════════════════════════

CUISINE_PREFERENCES: dict[str, list[str]] = {
    "es": ["spanish", "mexican", "mediterranean", "latin american", "italian"],
    "fr": ["french", "mediterranean", "italian", "moroccan"],
    "de": ["german", "austrian", "eastern european", "italian"],
    "it": ["italian", "mediterranean", "sicilian"],
    "pt": ["portuguese", "brazilian", "mediterranean"],
    "ar": ["middle_eastern", "moroccan", "lebanese", "mediterranean"],
    "hi": ["indian", "south asian", "sri lankan"],
    "zh": ["chinese", "cantonese", "sichuan", "taiwanese"],
    "ja": ["japanese", "korean", "asian"],
    "ko": ["korean", "japanese", "asian"],
    "tr": ["turkish", "middle_eastern", "mediterranean"],
    "th": ["thai", "vietnamese", "asian"],
    "vi": ["vietnamese", "thai", "asian"],
    "id": ["indonesian", "asian", "malaysian"],
    "ru": ["russian", "eastern european", "ukrainian"],
    "pl": ["polish", "eastern european"],
    "sv": ["swedish", "scandinavian", "nordic"],
    "da": ["danish", "scandinavian", "nordic"],
    "no": ["norwegian", "scandinavian", "nordic"],
    "fi": ["finnish", "scandinavian", "nordic"],
    "el": ["greek", "mediterranean"],
    "he": ["israeli", "middle_eastern", "mediterranean"],
}


def get_cuisine_preferences(language_code: str) -> list[str]:
    """Return preferred cuisines for a language, most preferred first."""
    return CUISINE_PREFERENCES.get(language_code, ["international"])


# ═══════════════════════════════════════════════════════════════════════════════
# 7. COMBINED PROFILE — single call to get everything for a user
# ═══════════════════════════════════════════════════════════════════════════════

def get_localisation_profile(language_code: str, month: Optional[int] = None) -> dict:
    """
    Return the complete localisation profile for a language code.
    Used by the /api/localisation/profile endpoint.
    """
    return {
        "language_code":       language_code,
        "measurement_system":  get_measurement_system(language_code),
        "unit_labels":         get_unit_labels(language_code),
        "currency":            get_currency(language_code),
        "dietary_defaults":    get_dietary_defaults(language_code),
        "cuisine_preferences": get_cuisine_preferences(language_code),
        "seasonal_produce":    get_seasonal_produce(language_code, month),
        "current_month":       month or datetime.now().month,
    }
