"""
cache.py — MongoDB-backed AI result cache
==========================================
Stores AI responses so identical requests are never repeated.

Collections used:
  - ai_cache          : general key/value cache with TTL
  - ingredient_aisles : permanent ingredient → aisle lookup table

Usage:
    from cache import get_cache, set_cache, get_aisle, set_aisle

All functions accept the db object from app.state.db.
"""

import re
import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Any
from urllib.parse import urlparse, parse_qs, urlencode


# ── TTL constants (in days) ───────────────────────────────────────────────────
TTL_NUTRITION   = 3650  # 10 years — calorie counts never change
TTL_URL_IMPORT  = 30    # recipe content is stable; bump from 7 to 30 days
TTL_YOUTUBE     = 30    # YouTube metadata
TTL_UNIT_CONV   = 3650  # unit conversions never change
TTL_MEAL_PLAN   = 1     # AI meal plans — regenerate daily


# ── URL normalisation (optimisation #4) ──────────────────────────────────────

# UTM and tracking params to strip before caching
_STRIP_PARAMS = {
    'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
    'utm_id', 'fbclid', 'gclid', 'ref', 'source', 'src', 'mc_cid', 'mc_eid',
    '_ga', 'igshid', 'epik', 'pp', 'feature', 'si', 'via',
}

def normalise_url(url: str) -> str:
    """
    Normalise a recipe URL for consistent cache key generation.
    Strips tracking params, www prefix, trailing slashes, fragments.
    Example:
      https://www.allrecipes.com/recipe/123/?utm_source=email&fbclid=xyz
      → allrecipes.com/recipe/123
    """
    try:
        parsed = urlparse(url.strip())
        # Strip www prefix
        host = parsed.netloc.lower()
        if host.startswith('www.'):
            host = host[4:]
        # Strip tracking query params
        qs = parse_qs(parsed.query, keep_blank_values=False)
        clean_qs = {k: v for k, v in qs.items() if k.lower() not in _STRIP_PARAMS}
        clean_query = urlencode(clean_qs, doseq=True)
        # Strip trailing slash from path, lowercase path
        path = parsed.path.rstrip('/')
        clean = f"{host}{path}"
        if clean_query:
            clean += f"?{clean_query}"
        return clean.lower()
    except Exception:
        return url.strip().rstrip('/').lower()


# ── Key builders ──────────────────────────────────────────────────────────────

def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:24]


def nutrition_key(ingredients: list, servings: int) -> str:
    canonical = json.dumps(ingredients, sort_keys=True) + f"|{servings}"
    return f"nutrition:v4:{_hash(canonical)}"   # v4: bracketed weights such as "500 g (4 cups)"


def url_import_key(url: str) -> str:
    """Cache key using normalised URL — strips tracking params, www, trailing slashes."""
    return f"url_import:v3:{_hash(normalise_url(url))}"  # v2: older entries held garbled steps


def youtube_key(video_id: str) -> str:
    return f"youtube:{video_id}"


def recipe_fingerprint(title: str, domain: str) -> str:
    """
    Fingerprint for deduplication check (optimisation #5).
    Normalises title to detect near-duplicates before importing.
    """
    clean_title = re.sub(r'[^a-z0-9 ]', '', title.lower())
    clean_title = re.sub(r'\s+', ' ', clean_title).strip()
    return _hash(f"{domain}:{clean_title}")


# ── Generic cache get/set ─────────────────────────────────────────────────────

async def get_cache(db, key: str) -> Optional[Any]:
    doc = await db.ai_cache.find_one({"key": key})
    if not doc:
        return None
    exp = doc.get("expires_at")
    if exp is not None and exp.tzinfo is None:      # MongoDB hands back naive datetimes
        exp = exp.replace(tzinfo=timezone.utc)
    if exp is not None and exp < datetime.now(timezone.utc):
        await db.ai_cache.delete_one({"key": key})
        return None
    return doc.get("value")


async def set_cache(db, key: str, value: Any, ttl_days: int = 30) -> None:
    expires = datetime.now(timezone.utc) + timedelta(days=ttl_days)
    await db.ai_cache.update_one(
        {"key": key},
        {"$set": {
            "key": key,
            "value": value,
            "expires_at": expires,
            "cached_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )


# ── Ingredient aisle lookup (permanent, no TTL) ───────────────────────────────

AISLE_LOOKUP = {
    # Produce
    "tomato": "Produce", "tomatoes": "Produce", "onion": "Produce", "onions": "Produce",
    "garlic": "Produce", "potato": "Produce", "potatoes": "Produce", "carrot": "Produce",
    "carrots": "Produce", "celery": "Produce", "bell pepper": "Produce", "lettuce": "Produce",
    "spinach": "Produce", "broccoli": "Produce", "mushroom": "Produce", "mushrooms": "Produce",
    "cucumber": "Produce", "zucchini": "Produce", "courgette": "Produce", "eggplant": "Produce",
    "aubergine": "Produce", "cabbage": "Produce", "cauliflower": "Produce", "kale": "Produce",
    "leek": "Produce", "leeks": "Produce", "avocado": "Produce", "lemon": "Produce",
    "lemons": "Produce", "lime": "Produce", "limes": "Produce", "orange": "Produce",
    "apple": "Produce", "banana": "Produce", "berries": "Produce", "strawberries": "Produce",
    "blueberries": "Produce", "mango": "Produce", "ginger": "Produce", "basil": "Produce",
    "cilantro": "Produce", "coriander": "Produce", "parsley": "Produce", "mint": "Produce",
    "rosemary": "Produce", "thyme": "Produce", "green onion": "Produce", "scallion": "Produce",
    "shallot": "Produce", "shallots": "Produce", "chives": "Produce", "sweet potato": "Produce",
    "pumpkin": "Produce", "squash": "Produce", "asparagus": "Produce", "peas": "Produce",
    "corn": "Produce", "green beans": "Produce", "beets": "Produce", "beetroot": "Produce",
    # Dairy & Eggs
    "milk": "Dairy", "butter": "Dairy", "egg": "Dairy", "eggs": "Dairy", "cheese": "Dairy",
    "cheddar": "Dairy", "parmesan": "Dairy", "mozzarella": "Dairy", "feta": "Dairy",
    "cream cheese": "Dairy", "cream": "Dairy", "heavy cream": "Dairy", "sour cream": "Dairy",
    "yogurt": "Dairy", "greek yogurt": "Dairy", "ricotta": "Dairy", "cottage cheese": "Dairy",
    "whipping cream": "Dairy", "half and half": "Dairy", "crème fraîche": "Dairy",
    # Meat
    "chicken": "Meat", "chicken breast": "Meat", "chicken thigh": "Meat", "ground beef": "Meat",
    "beef": "Meat", "steak": "Meat", "pork": "Meat", "bacon": "Meat", "ham": "Meat",
    "sausage": "Meat", "turkey": "Meat", "lamb": "Meat", "duck": "Meat", "prosciutto": "Meat",
    "pancetta": "Meat", "salami": "Meat", "chorizo": "Meat", "mince": "Meat",
    # Seafood
    "salmon": "Seafood", "shrimp": "Seafood", "prawns": "Seafood", "tuna": "Seafood",
    "cod": "Seafood", "tilapia": "Seafood", "mussels": "Seafood", "clams": "Seafood",
    "scallops": "Seafood", "crab": "Seafood", "lobster": "Seafood", "calamari": "Seafood",
    "squid": "Seafood", "anchovies": "Seafood", "sardines": "Seafood", "fish": "Seafood",
    # Grains / Pasta
    "rice": "Grains", "pasta": "Grains", "spaghetti": "Grains", "penne": "Grains",
    "noodles": "Grains", "bread": "Bakery", "sourdough": "Bakery", "tortilla": "Grains",
    "pita": "Bakery", "quinoa": "Grains", "couscous": "Grains", "oats": "Grains",
    "barley": "Grains", "breadcrumbs": "Grains", "panko": "Grains",
    # Canned & Jarred
    "tomato sauce": "Canned", "diced tomatoes": "Canned", "canned tomatoes": "Canned",
    "tomato paste": "Canned", "chickpeas": "Canned", "black beans": "Canned",
    "kidney beans": "Canned", "lentils": "Canned", "coconut milk": "Canned",
    "broth": "Canned", "stock": "Canned", "chicken broth": "Canned", "beef broth": "Canned",
    # Spices
    "salt": "Spices", "pepper": "Spices", "black pepper": "Spices", "cumin": "Spices",
    "paprika": "Spices", "turmeric": "Spices", "cinnamon": "Spices", "oregano": "Spices",
    "chili flakes": "Spices", "red pepper flakes": "Spices", "cayenne": "Spices",
    "bay leaf": "Spices", "bay leaves": "Spices", "nutmeg": "Spices", "cardamom": "Spices",
    "coriander powder": "Spices", "garam masala": "Spices", "curry powder": "Spices",
    "garlic powder": "Spices", "onion powder": "Spices", "chili powder": "Spices",
    # Oils & Condiments
    "olive oil": "Oils", "vegetable oil": "Oils", "coconut oil": "Oils", "sesame oil": "Oils",
    "soy sauce": "Condiments", "fish sauce": "Condiments", "worcestershire": "Condiments",
    "hot sauce": "Condiments", "ketchup": "Condiments", "mustard": "Condiments",
    "mayonnaise": "Condiments", "vinegar": "Condiments", "balsamic": "Condiments",
    "honey": "Condiments", "maple syrup": "Condiments", "sriracha": "Condiments",
    "tahini": "Condiments", "hoisin sauce": "Condiments", "oyster sauce": "Condiments",
    # Baking
    "flour": "Baking", "sugar": "Baking", "brown sugar": "Baking", "baking powder": "Baking",
    "baking soda": "Baking", "yeast": "Baking", "vanilla": "Baking", "cocoa powder": "Baking",
    "chocolate": "Baking", "cornstarch": "Baking", "powdered sugar": "Baking",
    "almond flour": "Baking", "vegetable shortening": "Baking",
    # Frozen
    "frozen peas": "Frozen", "frozen corn": "Frozen", "frozen spinach": "Frozen",
    "ice cream": "Frozen", "frozen berries": "Frozen",
    # Beverages
    "water": "Beverages", "wine": "Beverages", "beer": "Beverages",
    "chicken stock": "Beverages", "vegetable stock": "Beverages",
}


# Extra entries (expanded from the master recipes' most common ingredients)
AISLE_LOOKUP.update({
    "red chilli": "Produce",
    "green chilli": "Produce",
    "chilli": "Produce",
    "chilies": "Produce",
    "chillies": "Produce",
    "jalapeno": "Produce",
    "scotch bonnet": "Produce",
    "birds-eye chillies": "Produce",
    "dill": "Produce",
    "sage": "Produce",
    "tarragon": "Produce",
    "marjoram": "Produce",
    "rocket": "Produce",
    "fennel": "Produce",
    "fennel bulb": "Produce",
    "bean sprouts": "Produce",
    "swede": "Produce",
    "peaches": "Produce",
    "coconut": "Produce",
    "pomegranate": "Produce",
    "pomegranate seeds": "Produce",
    "challots": "Produce",
    "radish": "Produce",
    "turnip": "Produce",
    "parsnip": "Produce",
    "pak choi": "Produce",
    "bok choy": "Produce",
    "spring onion": "Produce",
    "spring onions": "Produce",
    "scallions": "Produce",
    "watercress": "Produce",
    "pear": "Produce",
    "pineapple": "Produce",
    "grapes": "Produce",
    "raspberries": "Produce",
    "cherries": "Produce",
    "plum": "Produce",
    "plums": "Produce",
    "apricot": "Produce",
    "figs": "Produce",
    "melon": "Produce",
    "watermelon": "Produce",
    "sweetcorn": "Produce",
    "okra": "Produce",
    "artichoke": "Produce",
    "celeriac": "Produce",
    "lemongrass": "Produce",
    "almonds": "Snacks",
    "walnuts": "Snacks",
    "peanuts": "Snacks",
    "pecans": "Snacks",
    "pine nuts": "Snacks",
    "cashew nuts": "Snacks",
    "cashews": "Snacks",
    "hazelnuts": "Snacks",
    "pistachios": "Snacks",
    "raisins": "Snacks",
    "sultanas": "Snacks",
    "dried apricots": "Snacks",
    "dates": "Snacks",
    "cranberries": "Snacks",
    "dried cranberries": "Snacks",
    "prunes": "Snacks",
    "ground almonds": "Snacks",
    "desiccated coconut": "Snacks",
    "sesame seed": "Snacks",
    "sesame seeds": "Snacks",
    "allspice": "Spices",
    "ground allspice": "Spices",
    "cloves": "Spices",
    "saffron": "Spices",
    "star anise": "Spices",
    "fennel seeds": "Spices",
    "chilli powder": "Spices",
    "chilli flakes": "Spices",
    "harissa spice": "Spices",
    "italian seasoning": "Spices",
    "seasoning": "Spices",
    "smoked paprika": "Spices",
    "mixed spice": "Spices",
    "mustard seeds": "Spices",
    "coriander seeds": "Spices",
    "dried thyme": "Spices",
    "peppercorns": "Spices",
    "vanilla extract": "Spices",
    "almond extract": "Spices",
    "fenugreek": "Spices",
    "sumac": "Spices",
    "za'atar": "Spices",
    "sunflower oil": "Oils",
    "sesame seed oil": "Oils",
    "canola oil": "Oils",
    "rapeseed oil": "Oils",
    "peanut oil": "Oils",
    "ground nut oil": "Oils",
    "groundnut oil": "Oils",
    "cooking oil": "Oils",
    "avocado oil": "Oils",
    "ghee": "Oils",
    "lard": "Oils",
    "suet": "Oils",
    "shortening": "Oils",
    "hotsauce": "Condiments",
    "sweet chilli sauce": "Condiments",
    "thai red curry paste": "Condiments",
    "red curry paste": "Condiments",
    "green curry paste": "Condiments",
    "tamarind paste": "Condiments",
    "tomato puree": "Condiments",
    "mirin": "Condiments",
    "capers": "Condiments",
    "olives": "Condiments",
    "black olives": "Condiments",
    "green olives": "Condiments",
    "jam": "Condiments",
    "dijon mustard": "Condiments",
    "balsamic vinegar": "Condiments",
    "worcestershire sauce": "Condiments",
    "pesto": "Condiments",
    "harissa": "Condiments",
    "miso": "Condiments",
    "gochujang": "Condiments",
    "chutney": "Condiments",
    "pickles": "Condiments",
    "gherkins": "Condiments",
    "molasses": "Baking",
    "golden syrup": "Baking",
    "black treacle": "Baking",
    "treacle": "Baking",
    "cocoa": "Baking",
    "bicarbonate of soda": "Baking",
    "starch": "Baking",
    "cornflour": "Baking",
    "dulce de leche": "Baking",
    "condensed milk": "Baking",
    "icing sugar": "Baking",
    "caster sugar": "Baking",
    "dark chocolate": "Baking",
    "chocolate chips": "Baking",
    "custard powder": "Baking",
    "gelatine": "Baking",
    "digestive biscuits": "Baking",
    "biscuits": "Baking",
    "pretzels": "Baking",
    "puff pastry": "Baking",
    "shortcrust pastry": "Baking",
    "filo pastry": "Baking",
    "pastry": "Baking",
    "creme fraiche": "Dairy",
    "mascarpone": "Dairy",
    "double cream": "Dairy",
    "single cream": "Dairy",
    "yoghurt": "Dairy",
    "buttermilk": "Dairy",
    "halloumi": "Dairy",
    "gruyere": "Dairy",
    "brie": "Dairy",
    "goats cheese": "Dairy",
    "paneer": "Dairy",
    "baguette": "Bakery",
    "naan": "Bakery",
    "pitta": "Bakery",
    "tortillas": "Bakery",
    "wraps": "Bakery",
    "burger buns": "Bakery",
    "rolls": "Bakery",
    "ciabatta": "Bakery",
    "croissant": "Bakery",
    "cannellini beans": "Canned",
    "broad beans": "Canned",
    "butter beans": "Canned",
    "haricot beans": "Canned",
    "borlotti beans": "Canned",
    "chopped tomatoes": "Canned",
    "passata": "Canned",
    "sweetcorn tin": "Canned",
    "tinned tomatoes": "Canned",
    "tinned tuna": "Canned",
    "brandy": "Beverages",
    "rum": "Beverages",
    "gin": "Beverages",
    "sake": "Beverages",
    "dry sherry": "Beverages",
    "sherry": "Beverages",
    "red wine": "Beverages",
    "white wine": "Beverages",
    "vodka": "Beverages",
    "whisky": "Beverages",
    "whiskey": "Beverages",
    "port": "Beverages",
    "marsala": "Beverages",
    "coffee": "Beverages",
    "espresso": "Beverages",
    "tea": "Beverages",
    "champagne": "Beverages",
    "prosecco": "Beverages",
    "cider": "Beverages",
    "tofu": "Meat",
    "tempeh": "Meat",
    "gammon": "Meat",
    "sausages": "Meat",
    "haddock": "Seafood",
})


_AISLE_PATTERNS = None


def lookup_aisle(ingredient_name: str) -> Optional[str]:
    """Exact match first, then whole-word match (longest known name wins, so 'olive oil' beats 'oil')."""
    global _AISLE_PATTERNS
    key = ingredient_name.lower().strip()
    if key in AISLE_LOOKUP:
        return AISLE_LOOKUP[key]
    if _AISLE_PATTERNS is None:
        import re
        _AISLE_PATTERNS = [
            (re.compile(r"(?<![a-z])" + re.escape(k) + r"(?:e?s)?(?![a-z])"), a)
            for k, a in sorted(AISLE_LOOKUP.items(), key=lambda kv: -len(kv[0]))
        ]
    for pattern, aisle in _AISLE_PATTERNS:
        if pattern.search(key):
            return aisle
    return None


async def get_aisle(db, ingredient_name: str) -> Optional[str]:
    aisle = lookup_aisle(ingredient_name)
    if aisle:
        return aisle
    key = f"aisle:{_hash(ingredient_name.lower().strip())}"
    cached = await db.ai_cache.find_one({"key": key})
    if cached:
        return cached.get("value")
    return None


async def set_aisle(db, ingredient_name: str, aisle: str) -> None:
    key = f"aisle:{_hash(ingredient_name.lower().strip())}"
    await db.ai_cache.update_one(
        {"key": key},
        {"$set": {
            "key": key,
            "value": aisle,
            "ingredient": ingredient_name.lower().strip(),
            "cached_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )


async def create_cache_indexes(db) -> None:
    await db.ai_cache.create_index("key", unique=True)
    await db.ai_cache.create_index("expires_at", expireAfterSeconds=0)
    await db.ai_cache.create_index("ingredient")
    # Deduplication index
    await db.recipes.create_index("import_fingerprint", sparse=True)


